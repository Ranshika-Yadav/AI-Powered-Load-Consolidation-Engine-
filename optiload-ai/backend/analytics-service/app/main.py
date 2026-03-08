"""
Analytics Service — OptiLoad AI
Aggregates metrics, generates KPIs, AI recommendations, 
and exposes Prometheus metrics
"""
import uuid
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import psycopg2
from psycopg2.extras import RealDictCursor
import redis
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic_settings import BaseSettings
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
import json

class Settings(BaseSettings):
    database_url: str = "postgresql://optiload:optiload_secret@localhost:5432/optiload_db"
    redis_url: str = "redis://localhost:6379/5"
    class Config:
        env_file = ".env"

settings = Settings()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="OptiLoad AI — Analytics Service",
    description="Dashboard metrics, KPIs, and AI recommendations",
    version="1.0.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
redis_client = redis.from_url(settings.redis_url, decode_responses=True)

# ── Prometheus Gauges ──────────────────────────────────────────────────────────
gauge_total_shipments = Gauge("optiload_total_shipments", "Total shipments in system")
gauge_pending_shipments = Gauge("optiload_pending_shipments", "Pending shipments")
gauge_avg_utilization = Gauge("optiload_avg_utilization_percent", "Average vehicle utilization")
gauge_total_routes = Gauge("optiload_total_routes", "Total optimized routes")
gauge_co2_saved = Gauge("optiload_co2_saved_kg", "CO2 saved vs baseline")
gauge_cost_saved = Gauge("optiload_cost_saved_inr", "Cost saved vs baseline")


def get_db():
    db_url = settings.database_url.replace("postgresql://", "")
    user_pass, rest = db_url.split("@")
    user, password = user_pass.split(":")
    host_db = rest.split("/")
    db = host_db[-1]
    host_port = host_db[0]
    host, port = (host_port.split(":") + ["5432"])[:2]
    return psycopg2.connect(host=host, port=port, dbname=db, user=user, password=password)


def generate_recommendations(routes: List[dict], shipments: List[dict], vehicles: List[dict]) -> List[dict]:
    """Generate AI consolidation and optimization recommendations."""
    recommendations = []
    
    # Find underutilized vehicles
    for r in routes:
        util = r.get("utilization_percent", 0)
        if util < 50:
            recommendations.append({
                "type": "underutilization",
                "severity": "high" if util < 30 else "medium",
                "title": f"Vehicle Underutilized ({util:.0f}%)",
                "description": f"Vehicle {str(r.get('vehicle_id',''))[:8]}... is only {util:.0f}% utilized. Consider consolidating nearby shipments.",
                "potential_saving_inr": round(r.get("total_cost_inr", 0) * 0.2, 0),
                "action": "consolidate",
            })

    # Find high-priority pending shipments
    pending = [s for s in shipments if s.get("status") == "pending"]
    high_priority = [s for s in pending if s.get("priority", 1) >= 4]
    if high_priority:
        recommendations.append({
            "type": "priority_alert",
            "severity": "high",
            "title": f"{len(high_priority)} High-Priority Shipments Pending",
            "description": f"There are {len(high_priority)} high-priority shipments awaiting assignment. Run optimization to reduce delivery delays.",
            "potential_saving_inr": len(high_priority) * 500,
            "action": "optimize",
        })

    # Find consolidation opportunities
    if len(pending) >= 3:
        # Group pending by origin proximity
        import math
        for i in range(min(5, len(pending) - 1)):
            for j in range(i + 1, min(i + 4, len(pending))):
                s1, s2 = pending[i], pending[j]
                try:
                    lat1, lng1 = float(s1.get("origin_lat", 0)), float(s1.get("origin_lng", 0))
                    lat2, lng2 = float(s2.get("origin_lat", 0)), float(s2.get("origin_lng", 0))
                    d = math.sqrt((lat1-lat2)**2 + (lng1-lng2)**2) * 111  # rough km
                    if d < 30:
                        base_cost = (
                            math.sqrt((float(s1.get("destination_lat",0))-lat1)**2 + (float(s1.get("destination_lng",0))-lng1)**2) * 111 * 15
                            + math.sqrt((float(s2.get("destination_lat",0))-lat2)**2 + (float(s2.get("destination_lng",0))-lng2)**2) * 111 * 15
                        )
                        saving = base_cost * 0.35
                        if saving > 100:
                            s1_id = str(s1.get("shipment_id",""))[:8]
                            s2_id = str(s2.get("shipment_id",""))[:8]
                            recommendations.append({
                                "type": "consolidation",
                                "severity": "medium",
                                "title": f"Consolidation Opportunity",
                                "description": f"Shipment #{s1_id} and #{s2_id} originate within {d:.0f}km. Consolidating could reduce cost by ₹{saving:.0f}.",
                                "shipment_ids": [str(s1.get("shipment_id","")), str(s2.get("shipment_id",""))],
                                "potential_saving_inr": round(saving, 0),
                                "action": "consolidate",
                            })
                except Exception:
                    continue
            if len(recommendations) >= 8:
                break

    # Return top 6
    return recommendations[:6]


@app.get("/health")
async def health():
    return {"status": "ok", "service": "analytics-service"}


@app.get("/metrics")
async def metrics_endpoint():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/metrics")
async def get_dashboard_metrics():
    """Main dashboard metrics endpoint. Cached for 30s."""
    cached = redis_client.get("analytics:dashboard")
    if cached:
        return json.loads(cached)

    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Shipment stats
            cur.execute("SELECT COUNT(*) as total, status FROM shipments GROUP BY status")
            ship_stats = {r["status"]: int(r["total"]) for r in cur.fetchall()}
            total_shipments = sum(ship_stats.values())
            pending = ship_stats.get("pending", 0)
            optimized = ship_stats.get("optimized", 0)

            # Vehicle stats
            cur.execute("SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE availability_status=TRUE) as active FROM vehicles")
            v_row = cur.fetchone()
            total_vehicles = int(v_row["total"] or 0)
            active_vehicles = int(v_row["active"] or 0)

            # Route / optimization stats
            cur.execute("""
                SELECT 
                    COUNT(*) as total_routes,
                    COALESCE(SUM(total_distance), 0) as total_distance,
                    COALESCE(SUM(total_cost), 0) as total_cost,
                    COALESCE(AVG(utilization_percent), 0) as avg_utilization,
                    COALESCE(SUM(estimated_co2), 0) as total_co2
                FROM routes
            """)
            r_row = cur.fetchone()
            total_routes = int(r_row["total_routes"] or 0)
            total_distance = float(r_row["total_distance"] or 0)
            total_cost = float(r_row["total_cost"] or 0)
            avg_utilization = float(r_row["avg_utilization"] or 0)
            total_co2 = float(r_row["total_co2"] or 0)

            # Compute baseline (unoptimized estimate)
            baseline_cost = total_cost * 1.4 if total_cost > 0 else 0
            cost_savings = baseline_cost - total_cost
            baseline_co2 = total_co2 * 1.35 if total_co2 > 0 else 0
            co2_savings = baseline_co2 - total_co2

            # Trips saved estimate
            trips_saved = max(0, total_shipments - total_routes) if total_routes > 0 else 0

            # Recent simulation
            cur.execute("SELECT * FROM simulation_results ORDER BY created_at DESC LIMIT 1")
            sim_row = cur.fetchone()
            latest_sim = dict(sim_row) if sim_row else None
            if latest_sim:
                for k, v in latest_sim.items():
                    if isinstance(v, uuid.UUID):
                        latest_sim[k] = str(v)
                    elif isinstance(v, datetime):
                        latest_sim[k] = v.isoformat()

            # Daily cost trend (last 7 days)
            cur.execute("""
                SELECT DATE(created_at) as date, COALESCE(SUM(total_cost), 0) as cost, COUNT(*) as routes
                FROM routes
                WHERE created_at >= NOW() - INTERVAL '7 days'
                GROUP BY DATE(created_at)
                ORDER BY date
            """)
            cost_trend = [{"date": str(r["date"]), "cost": float(r["cost"]), "routes": int(r["routes"])} for r in cur.fetchall()]

            # Fleet utilization distribution
            cur.execute("SELECT utilization_percent FROM routes ORDER BY created_at DESC LIMIT 50")
            util_rows = cur.fetchall()
            utilization_distribution = [float(r["utilization_percent"]) for r in util_rows]

            # Top routes
            cur.execute("SELECT * FROM routes ORDER BY total_cost DESC LIMIT 10")
            top_routes = []
            for r in cur.fetchall():
                d = dict(r)
                for k, v in d.items():
                    if isinstance(v, uuid.UUID):
                        d[k] = str(v)
                    elif isinstance(v, datetime):
                        d[k] = v.isoformat()
                    elif isinstance(v, list):
                        d[k] = [str(x) for x in v]
                top_routes.append(d)

            # Get shipments for recommendations
            cur.execute("SELECT * FROM shipments WHERE status='pending' LIMIT 20")
            pending_ships = [dict(r) for r in cur.fetchall()]
            for s in pending_ships:
                for k, v in s.items():
                    if isinstance(v, uuid.UUID):
                        s[k] = str(v)
                    elif isinstance(v, datetime):
                        s[k] = v.isoformat()
            recommendations = generate_recommendations(top_routes, pending_ships, [])

            # Update Prometheus gauges
            gauge_total_shipments.set(total_shipments)
            gauge_pending_shipments.set(pending)
            gauge_avg_utilization.set(avg_utilization)
            gauge_total_routes.set(total_routes)
            gauge_co2_saved.set(co2_savings)
            gauge_cost_saved.set(cost_savings)

            result = {
                "shipments": {
                    "total": total_shipments,
                    "pending": pending,
                    "optimized": optimized,
                    "by_status": ship_stats,
                },
                "vehicles": {
                    "total": total_vehicles,
                    "active": active_vehicles,
                    "avg_utilization_percent": round(avg_utilization, 1),
                },
                "routes": {
                    "total": total_routes,
                    "total_distance_km": round(total_distance, 1),
                    "total_cost_inr": round(total_cost, 2),
                },
                "optimization": {
                    "avg_utilization_percent": round(avg_utilization, 1),
                    "trips_saved": trips_saved,
                    "cost_savings_inr": round(cost_savings, 2),
                    "cost_reduction_percent": round((cost_savings / baseline_cost * 100) if baseline_cost > 0 else 0, 1),
                },
                "carbon": {
                    "total_co2_kg": round(total_co2, 2),
                    "co2_saved_kg": round(co2_savings, 2),
                    "co2_reduction_percent": round((co2_savings / baseline_co2 * 100) if baseline_co2 > 0 else 0, 1),
                    "trees_equivalent": round(co2_savings / 21.77, 1),
                },
                "cost_trend": cost_trend,
                "utilization_distribution": utilization_distribution,
                "top_routes": top_routes,
                "recommendations": recommendations,
                "latest_simulation": latest_sim,
                "last_updated": datetime.utcnow().isoformat(),
            }

            redis_client.setex("analytics:dashboard", 30, json.dumps(result))
            return result

    except Exception as e:
        logger.error(f"Analytics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.get("/api/metrics/kpi")
async def kpi_summary():
    """Lightweight KPI summary for header bars."""
    cached = redis_client.get("analytics:kpi")
    if cached:
        return json.loads(cached)
    full = await get_dashboard_metrics()
    kpi = {
        "total_shipments": full["shipments"]["total"],
        "pending_shipments": full["shipments"]["pending"],
        "avg_utilization": full["vehicles"]["avg_utilization_percent"],
        "trips_saved": full["optimization"]["trips_saved"],
        "cost_savings_inr": full["optimization"]["cost_savings_inr"],
        "co2_saved_kg": full["carbon"]["co2_saved_kg"],
        "total_routes": full["routes"]["total"],
    }
    redis_client.setex("analytics:kpi", 30, json.dumps(kpi))
    return kpi


@app.get("/api/recommendations")
async def get_recommendations():
    """Get AI recommendations."""
    full = await get_dashboard_metrics()
    return {"recommendations": full.get("recommendations", [])}


@app.get("/api/metrics/history")
async def metrics_history(days: int = 7):
    """Historical metrics for trend charts."""
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as routes,
                    COALESCE(SUM(total_cost), 0) as total_cost,
                    COALESCE(AVG(utilization_percent), 0) as avg_utilization,
                    COALESCE(SUM(estimated_co2), 0) as total_co2
                FROM routes
                WHERE created_at >= NOW() - INTERVAL '%s days'
                GROUP BY DATE(created_at)
                ORDER BY date
            """, (days,))
            rows = cur.fetchall()
            return [
                {
                    "date": str(r["date"]),
                    "routes": int(r["routes"]),
                    "total_cost": round(float(r["total_cost"]), 2),
                    "avg_utilization": round(float(r["avg_utilization"]), 1),
                    "total_co2": round(float(r["total_co2"]), 2),
                }
                for r in rows
            ]
    finally:
        conn.close()
