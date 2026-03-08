"""
Clustering Service — OptiLoad AI
Detects compatible shipments and builds clusters using:
- Haversine distance
- Cosine similarity
- Time window overlap
- NetworkX graph + community detection
- DBSCAN + KMeans hybrid clustering
"""
import uuid
import logging
import math
from datetime import datetime
from typing import List, Optional, Dict, Any

import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor
import redis
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import json
from celery import Celery

# ── Settings ──────────────────────────────────────────────────────────────────
class Settings(BaseSettings):
    database_url: str = "postgresql://optiload:optiload_secret@localhost:5432/optiload_db"
    redis_url: str = "redis://localhost:6379/2"
    rabbitmq_url: str = "amqp://optiload:optiload_rabbit@localhost:5672/"

    class Config:
        env_file = ".env"


settings = Settings()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="OptiLoad AI — Clustering Service",
    description="Shipment clustering using graph models and ML algorithms",
    version="1.0.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

redis_client = redis.from_url(settings.redis_url, decode_responses=True)
celery_app = Celery("clustering", broker=settings.rabbitmq_url, backend=settings.redis_url)

# ── Metrics ────────────────────────────────────────────────────────────────────
clusters_created = Counter("clustering_clusters_total", "Clusters created")
clustering_duration = Histogram("clustering_duration_seconds", "Clustering duration")


# ── DB ─────────────────────────────────────────────────────────────────────────
def get_db():
    db_url = settings.database_url.replace("postgresql://", "")
    user_pass, rest = db_url.split("@")
    user, password = user_pass.split(":")
    host_db = rest.split("/")
    db = host_db[-1]
    host_port = host_db[0]
    host, port = (host_port.split(":") + ["5432"])[:2]
    return psycopg2.connect(host=host, port=port, dbname=db, user=user, password=password)


# ── Core Algorithms ────────────────────────────────────────────────────────────
def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    a, b = np.array(v1), np.array(v2)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def time_window_overlap(pickup_a: datetime, deadline_a: datetime,
                        pickup_b: datetime, deadline_b: datetime,
                        threshold_hours: float = 4.0) -> float:
    overlap_start = max(pickup_a, pickup_b)
    overlap_end = min(deadline_a, deadline_b)
    overlap_seconds = max(0, (overlap_end - overlap_start).total_seconds())
    overlap_hours = overlap_seconds / 3600
    return overlap_hours


def compute_compatibility(s1: dict, s2: dict,
                          geo_weight: float = 0.4,
                          route_weight: float = 0.4,
                          time_weight: float = 0.2,
                          max_distance_km: float = 100.0) -> float:
    """Compute composite compatibility score between two shipments [0, 1]."""
    # 1. Geospatial distance (origin to origin)
    origin_dist = haversine(s1["origin_lat"], s1["origin_lng"], s2["origin_lat"], s2["origin_lng"])
    geo_score = max(0.0, 1.0 - origin_dist / max_distance_km)

    # Destination distance
    dest_dist = haversine(s1["destination_lat"], s1["destination_lng"], s2["destination_lat"], s2["destination_lng"])
    dest_score = max(0.0, 1.0 - dest_dist / max_distance_km)
    geo_score = (geo_score + dest_score) / 2

    # 2. Route vector cosine similarity
    v1 = [s1["origin_lat"], s1["origin_lng"], s1["destination_lat"], s1["destination_lng"]]
    v2 = [s2["origin_lat"], s2["origin_lng"], s2["destination_lat"], s2["destination_lng"]]
    route_score = (cosine_similarity(v1, v2) + 1) / 2  # normalize [-1,1] -> [0,1]

    # 3. Time window overlap
    pickup_a = s1["pickup_time"] if isinstance(s1["pickup_time"], datetime) else datetime.fromisoformat(str(s1["pickup_time"]))
    deadline_a = s1["delivery_deadline"] if isinstance(s1["delivery_deadline"], datetime) else datetime.fromisoformat(str(s1["delivery_deadline"]))
    pickup_b = s2["pickup_time"] if isinstance(s2["pickup_time"], datetime) else datetime.fromisoformat(str(s2["pickup_time"]))
    deadline_b = s2["delivery_deadline"] if isinstance(s2["delivery_deadline"], datetime) else datetime.fromisoformat(str(s2["delivery_deadline"]))
    overlap_hours = time_window_overlap(pickup_a, deadline_a, pickup_b, deadline_b)
    time_score = min(1.0, overlap_hours / 24.0)

    return geo_weight * geo_score + route_weight * route_score + time_weight * time_score


def build_compatibility_graph(shipments: List[dict], threshold: float = 0.4):
    """Build NetworkX compatibility graph."""
    try:
        import networkx as nx
    except ImportError:
        logger.warning("networkx not available, using simplified clustering")
        return None, {}

    G = nx.Graph()
    for s in shipments:
        G.add_node(str(s["shipment_id"]), **{k: str(v) for k, v in s.items()})

    for i in range(len(shipments)):
        for j in range(i + 1, len(shipments)):
            score = compute_compatibility(shipments[i], shipments[j])
            if score >= threshold:
                G.add_edge(str(shipments[i]["shipment_id"]),
                           str(shipments[j]["shipment_id"]),
                           weight=score)
    return G, {}


def detect_communities(G) -> Dict[str, int]:
    """Run community detection on the graph."""
    try:
        import networkx as nx
        from networkx.algorithms import community
        communities = community.greedy_modularity_communities(G)
        mapping = {}
        for idx, comm in enumerate(communities):
            for node in comm:
                mapping[node] = idx
        return mapping
    except Exception as e:
        logger.warning(f"Community detection failed: {e}")
        return {}


def dbscan_cluster(shipments: List[dict], eps_km: float = 50.0, min_samples: int = 2) -> Dict[str, int]:
    """DBSCAN clustering on origin coordinates."""
    try:
        from sklearn.cluster import DBSCAN
    except ImportError:
        return {}

    if len(shipments) < 2:
        return {str(s["shipment_id"]): 0 for s in shipments}

    coords = np.array([[s["origin_lat"], s["origin_lng"]] for s in shipments])
    eps_rad = eps_km / 6371.0  # convert km to radians
    coords_rad = np.radians(coords)
    db = DBSCAN(eps=eps_rad, min_samples=min(min_samples, len(shipments)), algorithm="ball_tree", metric="haversine").fit(coords_rad)
    return {str(s["shipment_id"]): int(label) for s, label in zip(shipments, db.labels_)}


def kmeans_cluster(shipments: List[dict], n_clusters: int = None) -> Dict[str, int]:
    """KMeans clustering on route vectors."""
    try:
        from sklearn.cluster import KMeans
    except ImportError:
        return {}

    if len(shipments) < 2:
        return {str(s["shipment_id"]): 0 for s in shipments}

    k = n_clusters or max(2, min(len(shipments) // 5, 10))
    features = np.array([
        [s["origin_lat"], s["origin_lng"], s["destination_lat"], s["destination_lng"]]
        for s in shipments
    ])
    km = KMeans(n_clusters=k, random_state=42, n_init=10).fit(features)
    return {str(s["shipment_id"]): int(label) for s, label in zip(shipments, km.labels_)}


def hybrid_cluster(shipments: List[dict]) -> List[dict]:
    """
    Hybrid clustering: DBSCAN + KMeans + Graph community detection.
    Returns list of cluster objects.
    """
    n = len(shipments)
    if n == 0:
        return []

    # 1. DBSCAN
    dbscan_labels = dbscan_cluster(shipments)
    # 2. KMeans
    kmeans_labels = kmeans_cluster(shipments)
    # 3. Graph
    G, _ = build_compatibility_graph(shipments, threshold=0.35)
    graph_labels = {}
    if G and len(G.edges()) > 0:
        graph_labels = detect_communities(G)

    # Combine: majority vote / DBSCAN priority
    final_labels: Dict[str, int] = {}
    cluster_counter = 0
    for s in shipments:
        sid = str(s["shipment_id"])
        db_label = dbscan_labels.get(sid, -1)
        km_label = kmeans_labels.get(sid, 0)
        gr_label = graph_labels.get(sid, -1)

        if db_label >= 0:  # DBSCAN wins if it's not noise
            final_labels[sid] = db_label
        elif gr_label >= 0:
            final_labels[sid] = gr_label + 100  # offset to avoid collision
        else:
            final_labels[sid] = km_label + 200

    # Build cluster objects
    cluster_map: Dict[int, List[dict]] = {}
    for s in shipments:
        sid = str(s["shipment_id"])
        label = final_labels.get(sid, 0)
        if label not in cluster_map:
            cluster_map[label] = []
        cluster_map[label].append(s)

    clusters = []
    for label, members in cluster_map.items():
        if not members:
            continue
        total_weight = sum(s["weight"] for s in members)
        total_volume = sum(s["volume"] for s in members)
        centroid_lat = np.mean([s["origin_lat"] for s in members])
        centroid_lng = np.mean([s["origin_lng"] for s in members])
        clusters.append({
            "cluster_id": str(uuid.uuid4()),
            "shipment_ids": [str(s["shipment_id"]) for s in members],
            "cluster_weight": round(total_weight, 2),
            "cluster_volume": round(total_volume, 2),
            "centroid_lat": float(centroid_lat),
            "centroid_lng": float(centroid_lng),
            "size": len(members),
            "algorithm": "hybrid_dbscan_kmeans_graph",
        })

    return clusters


def save_clusters(clusters: List[dict], conn) -> List[str]:
    """Persist clusters to DB."""
    saved_ids = []
    with conn.cursor() as cur:
        for c in clusters:
            # Convert list to PostgreSQL array format
            ship_ids_arr = "{" + ",".join(c["shipment_ids"]) + "}"
            cur.execute(
                """INSERT INTO clusters 
                   (cluster_id, shipment_ids, cluster_weight, cluster_volume,
                    centroid_lat, centroid_lng, algorithm)
                   VALUES (%s, %s::uuid[], %s, %s, %s, %s, %s)""",
                (
                    c["cluster_id"],
                    ship_ids_arr,
                    c["cluster_weight"],
                    c["cluster_volume"],
                    c["centroid_lat"],
                    c["centroid_lng"],
                    c["algorithm"],
                ),
            )
            # Update shipments with cluster_id
            for sid in c["shipment_ids"]:
                cur.execute("UPDATE shipments SET cluster_id=%s WHERE shipment_id=%s",
                            (c["cluster_id"], sid))
            saved_ids.append(c["cluster_id"])
    return saved_ids


# ── Routes ─────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "service": "clustering-service"}


@app.get("/metrics")
async def metrics_endpoint():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/api/clusters/run")
async def run_clustering(background_tasks: BackgroundTasks, min_cluster_size: int = 2):
    """Run hybrid clustering on all pending shipments."""
    cached = redis_client.get("clusters:latest")
    if cached:
        return json.loads(cached)

    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM shipments WHERE status='pending' ORDER BY created_at DESC LIMIT 500")
            rows = cur.fetchall()
            shipments = []
            for r in rows:
                d = dict(r)
                for k, v in d.items():
                    if isinstance(v, uuid.UUID):
                        d[k] = str(v)
                shipments.append(d)

        if not shipments:
            return {"message": "No pending shipments to cluster", "clusters": []}

        with clustering_duration.time():
            clusters = hybrid_cluster(shipments)

        saved_ids = save_clusters(clusters, conn)
        conn.commit()

        # Enriched response
        result = {
            "total_shipments": len(shipments),
            "num_clusters": len(clusters),
            "cluster_ids": saved_ids,
            "clusters": clusters,
        }
        redis_client.setex("clusters:latest", 60, json.dumps(result))
        clusters_created.inc(len(clusters))
        logger.info(f"Created {len(clusters)} clusters from {len(shipments)} shipments")
        return result
    except Exception as e:
        conn.rollback()
        logger.error(f"Clustering failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.get("/api/clusters")
async def list_clusters(limit: int = 50):
    """List all clusters."""
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM clusters ORDER BY created_at DESC LIMIT %s", (limit,))
            rows = cur.fetchall()
            result = []
            for r in rows:
                d = dict(r)
                for k, v in d.items():
                    if isinstance(v, uuid.UUID):
                        d[k] = str(v)
                    elif isinstance(v, datetime):
                        d[k] = v.isoformat()
                    elif isinstance(v, list):
                        d[k] = [str(x) for x in v]
                result.append(d)
            return result
    finally:
        conn.close()


@app.get("/api/clusters/{cluster_id}")
async def get_cluster(cluster_id: str):
    """Get a specific cluster with its shipments."""
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM clusters WHERE cluster_id=%s", (cluster_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Cluster not found")
            d = dict(row)
            # Fetch shipments in cluster
            ship_ids = [str(x) for x in (d.get("shipment_ids") or [])]
            if ship_ids:
                cur.execute("SELECT * FROM shipments WHERE shipment_id = ANY(%s::uuid[])", (ship_ids,))
                shipments = cur.fetchall()
                d["shipments"] = [dict(s) for s in shipments]
            for k, v in d.items():
                if isinstance(v, uuid.UUID):
                    d[k] = str(v)
                elif isinstance(v, datetime):
                    d[k] = v.isoformat()
            return d
    finally:
        conn.close()


@app.post("/api/clusters/compatibility-check")
async def check_compatibility(shipment_id_a: str, shipment_id_b: str):
    """Check compatibility score between two shipments."""
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM shipments WHERE shipment_id=%s", (shipment_id_a,))
            s1 = cur.fetchone()
            cur.execute("SELECT * FROM shipments WHERE shipment_id=%s", (shipment_id_b,))
            s2 = cur.fetchone()
            if not s1 or not s2:
                raise HTTPException(status_code=404, detail="One or both shipments not found")
            score = compute_compatibility(dict(s1), dict(s2))
            dist = haversine(s1["origin_lat"], s1["origin_lng"], s2["origin_lat"], s2["origin_lng"])
            return {
                "shipment_a": shipment_id_a,
                "shipment_b": shipment_id_b,
                "compatibility_score": round(score, 4),
                "origin_distance_km": round(dist, 2),
                "compatible": score >= 0.4,
            }
    finally:
        conn.close()
