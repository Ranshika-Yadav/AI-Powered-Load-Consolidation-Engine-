"""
Optimization Service — OptiLoad AI
OR-Tools VRP, PuLP MILP, bin packing, carbon emission calculation
"""
import uuid
import logging
import math
from datetime import datetime
from typing import List, Dict, Any, Optional

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

# ── Settings ───────────────────────────────────────────────────────────────────
class Settings(BaseSettings):
    database_url: str = "postgresql://optiload:optiload_secret@localhost:5432/optiload_db"
    redis_url: str = "redis://localhost:6379/3"
    rabbitmq_url: str = "amqp://optiload:optiload_rabbit@localhost:5672/"
    alpha: float = 0.3   # distance weight
    beta: float = 0.2    # empty capacity weight
    gamma: float = 0.2   # trips weight
    delta: float = 0.2   # carbon weight
    epsilon: float = 0.1 # delay penalty weight
    emission_factor: float = 2.68  # kg CO2 per liter diesel
    class Config:
        env_file = ".env"


settings = Settings()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="OptiLoad AI — Optimization Service",
    description="VRP, MILP, and bin-packing load optimization",
    version="1.0.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

redis_client = redis.from_url(settings.redis_url, decode_responses=True)
celery_app = Celery("optimization", broker=settings.rabbitmq_url, backend=settings.redis_url)

optimization_runs = Counter("optimization_runs_total", "Optimization runs", ["algorithm"])
opt_duration = Histogram("optimization_duration_seconds", "Optimization run time")


def get_db():
    db_url = settings.database_url.replace("postgresql://", "")
    user_pass, rest = db_url.split("@")
    user, password = user_pass.split(":")
    host_db = rest.split("/")
    db = host_db[-1]
    host_port = host_db[0]
    host, port = (host_port.split(":") + ["5432"])[:2]
    return psycopg2.connect(host=host, port=port, dbname=db, user=user, password=password)


def haversine(lat1, lng1, lat2, lng2) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def calculate_co2(distance_km: float, fuel_efficiency_km_per_l: float) -> float:
    """Calculate kg CO2 for a trip."""
    liters = distance_km / fuel_efficiency_km_per_l
    return liters * settings.emission_factor


def first_fit_decreasing(shipments: List[dict], vehicles: List[dict]) -> List[dict]:
    """
    First Fit Decreasing bin packing heuristic.
    Returns list of route assignments: {vehicle_id, shipment_ids, utilization}.
    """
    # Sort shipments by volume descending
    sorted_shipments = sorted(shipments, key=lambda s: s["volume"], reverse=True)

    # Track remaining capacity per vehicle
    vehicle_remaining_vol = {str(v["vehicle_id"]): v["capacity_volume"] for v in vehicles}
    vehicle_remaining_wt = {str(v["vehicle_id"]): v["capacity_weight"] for v in vehicles}
    assignments: Dict[str, List[str]] = {str(v["vehicle_id"]): [] for v in vehicles}

    unassigned = []
    for shipment in sorted_shipments:
        placed = False
        # Find vehicle with smallest sufficient remaining capacity (best fit variant)
        best_vehicle = None
        best_remaining = float("inf")
        for v in vehicles:
            vid = str(v["vehicle_id"])
            if (vehicle_remaining_vol[vid] >= shipment["volume"] and
                    vehicle_remaining_wt[vid] >= shipment["weight"]):
                if vehicle_remaining_vol[vid] < best_remaining:
                    best_remaining = vehicle_remaining_vol[vid]
                    best_vehicle = vid
        if best_vehicle:
            assignments[best_vehicle].append(str(shipment["shipment_id"]))
            vehicle_remaining_vol[best_vehicle] -= shipment["volume"]
            vehicle_remaining_wt[best_vehicle] -= shipment["weight"]
            placed = True
        if not placed:
            unassigned.append(str(shipment["shipment_id"]))

    routes = []
    for v in vehicles:
        vid = str(v["vehicle_id"])
        sids = assignments[vid]
        if not sids:
            continue
        assigned_shipments = [s for s in shipments if str(s["shipment_id"]) in sids]
        used_vol = sum(s["volume"] for s in assigned_shipments)
        used_wt = sum(s["weight"] for s in assigned_shipments)
        utilization_vol = (used_vol / v["capacity_volume"]) * 100 if v["capacity_volume"] > 0 else 0
        utilization_wt = (used_wt / v["capacity_weight"]) * 100 if v["capacity_weight"] > 0 else 0
        utilization = (utilization_vol + utilization_wt) / 2

        # Estimate total distance (TSP approximation: nearest neighbor)
        if assigned_shipments:
            total_distance = estimate_route_distance(assigned_shipments, v)
        else:
            total_distance = 0.0

        total_cost = total_distance * v["cost_per_km"]
        co2 = calculate_co2(total_distance, v["fuel_efficiency"])

        routes.append({
            "route_id": str(uuid.uuid4()),
            "vehicle_id": vid,
            "vehicle_type": v["vehicle_type"],
            "shipment_ids": sids,
            "num_shipments": len(sids),
            "total_distance_km": round(total_distance, 2),
            "total_cost_inr": round(total_cost, 2),
            "utilization_percent": round(utilization, 2),
            "estimated_co2_kg": round(co2, 2),
            "fuel_consumption_l": round(total_distance / v["fuel_efficiency"], 2),
        })

    return routes, unassigned


def estimate_route_distance(shipments: List[dict], vehicle: dict) -> float:
    """Nearest-neighbor TSP approximation for route distance."""
    if not shipments:
        return 0.0
    # Start from vehicle current location
    cur_lat = vehicle.get("current_lat") or shipments[0]["origin_lat"]
    cur_lng = vehicle.get("current_lng") or shipments[0]["origin_lng"]
    visited = set()
    total = 0.0

    remaining = list(range(len(shipments)))
    while remaining:
        best_idx = min(remaining,
                       key=lambda i: haversine(cur_lat, cur_lng,
                                               shipments[i]["origin_lat"], shipments[i]["origin_lng"]))
        s = shipments[best_idx]
        # Travel to pickup
        total += haversine(cur_lat, cur_lng, s["origin_lat"], s["origin_lng"])
        # Travel to delivery
        total += haversine(s["origin_lat"], s["origin_lng"], s["destination_lat"], s["destination_lng"])
        cur_lat, cur_lng = s["destination_lat"], s["destination_lng"]
        remaining.remove(best_idx)

    return total


def run_vrp_ortools(shipments: List[dict], vehicles: List[dict]) -> Dict:
    """Run OR-Tools VRP solver."""
    try:
        from ortools.constraint_solver import routing_enums_pb2
        from ortools.constraint_solver import pywrapcp
    except ImportError:
        logger.warning("OR-Tools not available, falling back to FFD heuristic")
        routes, unassigned = first_fit_decreasing(shipments, vehicles)
        return {"algorithm": "ffd_fallback", "routes": routes, "unassigned": unassigned}

    if not shipments or not vehicles:
        return {"algorithm": "vrp_ortools", "routes": [], "unassigned": []}

    # Build locations: vehicle depots + shipment pickups + deliveries
    locations = []
    for v in vehicles:
        lat = v.get("current_lat") or shipments[0]["origin_lat"]
        lng = v.get("current_lng") or shipments[0]["origin_lng"]
        locations.append((lat, lng))

    pickup_indices = []
    delivery_indices = []
    for s in shipments:
        pickup_indices.append(len(locations))
        locations.append((s["origin_lat"], s["origin_lng"]))
        delivery_indices.append(len(locations))
        locations.append((s["destination_lat"], s["destination_lng"]))

    n = len(locations)
    # Distance matrix (in meters * 100 for integer solver)
    dist_matrix = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                d = haversine(locations[i][0], locations[i][1], locations[j][0], locations[j][1])
                dist_matrix[i][j] = int(d * 1000)  # meters

    manager = pywrapcp.RoutingIndexManager(n, len(vehicles), list(range(len(vehicles))), list(range(len(vehicles))))
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return dist_matrix[from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Capacity constraints
    def demand_callback(from_index):
        from_node = manager.IndexToNode(from_index)
        if from_node < len(vehicles):
            return 0  # depot
        shipment_idx = (from_node - len(vehicles)) // 2
        is_pickup = (from_node - len(vehicles)) % 2 == 0
        if shipment_idx < len(shipments):
            return int(shipments[shipment_idx]["volume"] * 100) if is_pickup else -int(shipments[shipment_idx]["volume"] * 100)
        return 0

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    cap = [int(v["capacity_volume"] * 100) for v in vehicles]
    routing.AddDimensionWithVehicleCapacity(demand_callback_index, 0, cap, True, "Capacity")

    # Pickup and delivery pairs
    for i, s in enumerate(shipments):
        pickup_idx = manager.NodeToIndex(pickup_indices[i])
        delivery_idx = manager.NodeToIndex(delivery_indices[i])
        routing.AddPickupAndDelivery(pickup_idx, delivery_idx)
        routing.solver().Add(routing.VehicleVar(pickup_idx) == routing.VehicleVar(delivery_idx))
        routing.solver().Add(
            routing.CumulVar(pickup_idx, "Capacity") <= routing.CumulVar(delivery_idx, "Capacity")
        )

    search_params = pywrapcp.DefaultRoutingSearchParameters()
    search_params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
    search_params.time_limit.seconds = 4

    solution = routing.SolveWithParameters(search_params)
    routes = []
    unassigned = []

    if solution:
        for v_idx, v in enumerate(vehicles):
            index = routing.Start(v_idx)
            route_shipments = []
            total_dist = 0
            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                if node >= len(vehicles):
                    s_idx = (node - len(vehicles)) // 2
                    if s_idx < len(shipments) and (node - len(vehicles)) % 2 == 0:
                        route_shipments.append(str(shipments[s_idx]["shipment_id"]))
                next_index = solution.Value(routing.NextVar(index))
                total_dist += routing.GetArcCostForVehicle(index, next_index, v_idx)
                index = next_index

            if route_shipments:
                dist_km = total_dist / 1000
                total_cost = dist_km * v["cost_per_km"]
                co2 = calculate_co2(dist_km, v["fuel_efficiency"])
                assigned_s = [s for s in shipments if str(s["shipment_id"]) in route_shipments]
                used_vol = sum(s["volume"] for s in assigned_s)
                utilization = (used_vol / v["capacity_volume"]) * 100 if v["capacity_volume"] > 0 else 0
                routes.append({
                    "route_id": str(uuid.uuid4()),
                    "vehicle_id": str(v["vehicle_id"]),
                    "vehicle_type": v["vehicle_type"],
                    "shipment_ids": route_shipments,
                    "num_shipments": len(route_shipments),
                    "total_distance_km": round(dist_km, 2),
                    "total_cost_inr": round(total_cost, 2),
                    "utilization_percent": round(utilization, 2),
                    "estimated_co2_kg": round(co2, 2),
                    "fuel_consumption_l": round(dist_km / v["fuel_efficiency"], 2),
                })
    else:
        # If solver fails, fallback to FFD
        routes, unassigned = first_fit_decreasing(shipments, vehicles)

    return {"algorithm": "vrp_ortools", "routes": routes, "unassigned": unassigned}


def run_milp_pulp(shipments: List[dict], vehicles: List[dict]) -> Dict:
    """
    PuLP MILP optimization.
    Decision: x[i][j] = 1 if shipment i assigned to vehicle j
    Objective: min α·distance + β·empty_cap + γ·trips + δ·CO2 + ε·delay
    """
    try:
        import pulp
    except ImportError:
        logger.warning("PuLP not available")
        return {"algorithm": "milp_fallback", "routes": [], "unassigned": []}

    prob = pulp.LpProblem("LoadOptimization", pulp.LpMinimize)
    I = range(len(shipments))
    J = range(len(vehicles))

    x = pulp.LpVariable.dicts("assign", [(i, j) for i in I for j in J], cat="Binary")

    # Compute route costs
    ship_weights = [s["weight"] for s in shipments]
    ship_volumes = [s["volume"] for s in shipments]
    veh_cap_wt = [v["capacity_weight"] for v in vehicles]
    veh_cap_vol = [v["capacity_volume"] for v in vehicles]
    veh_cost_km = [v["cost_per_km"] for v in vehicles]
    veh_fuel = [v["fuel_efficiency"] for v in vehicles]

    # Estimate dist for each shipment (origin→destination)
    ship_distances = [haversine(s["origin_lat"], s["origin_lng"], s["destination_lat"], s["destination_lng"]) for s in shipments]

    # Objective
    distance_cost = pulp.lpSum(
        x[i, j] * ship_distances[i] * veh_cost_km[j]
        for i in I for j in J
    )
    empty_cap_cost = pulp.lpSum(
        (1 - pulp.lpSum(x[i, j] * ship_volumes[i] for i in I) / veh_cap_vol[j]) * 100
        for j in J if veh_cap_vol[j] > 0
    )
    trips_cost = pulp.lpSum(
        pulp.lpSum(x[i, j] for i in I) > 0  # handled via binary trick below
        for j in J
    )
    co2_cost = pulp.lpSum(
        x[i, j] * ship_distances[i] / veh_fuel[j] * settings.emission_factor
        for i in I for j in J
    )

    prob += (settings.alpha * distance_cost +
             settings.beta * empty_cap_cost +
             settings.delta * co2_cost)

    # Constraints
    # Each shipment assigned to exactly one vehicle
    for i in I:
        prob += pulp.lpSum(x[i, j] for j in J) == 1

    # Vehicle weight capacity
    for j in J:
        prob += pulp.lpSum(x[i, j] * ship_weights[i] for i in I) <= veh_cap_wt[j]

    # Vehicle volume capacity
    for j in J:
        prob += pulp.lpSum(x[i, j] * ship_volumes[i] for i in I) <= veh_cap_vol[j]

    solver = pulp.PULP_CBC_CMD(msg=0, timeLimit=4)
    prob.solve(solver)

    routes = []
    unassigned = []
    if pulp.LpStatus[prob.status] in ("Optimal", "Feasible"):
        for j, v in enumerate(vehicles):
            assigned_sids = []
            for i, s in enumerate(shipments):
                if x[i, j].value() and x[i, j].value() > 0.5:
                    assigned_sids.append(str(s["shipment_id"]))
            if not assigned_sids:
                continue
            assigned_s = [s for s in shipments if str(s["shipment_id"]) in assigned_sids]
            total_dist = sum(ship_distances[i] for i, s in enumerate(shipments) if str(s["shipment_id"]) in assigned_sids)
            total_cost = total_dist * v["cost_per_km"]
            co2 = calculate_co2(total_dist, v["fuel_efficiency"])
            used_vol = sum(s["volume"] for s in assigned_s)
            utilization = (used_vol / v["capacity_volume"]) * 100 if v["capacity_volume"] > 0 else 0
            routes.append({
                "route_id": str(uuid.uuid4()),
                "vehicle_id": str(v["vehicle_id"]),
                "vehicle_type": v["vehicle_type"],
                "shipment_ids": assigned_sids,
                "num_shipments": len(assigned_sids),
                "total_distance_km": round(total_dist, 2),
                "total_cost_inr": round(total_cost, 2),
                "utilization_percent": round(utilization, 2),
                "estimated_co2_kg": round(co2, 2),
                "fuel_consumption_l": round(total_dist / v["fuel_efficiency"], 2),
            })
    else:
        routes, unassigned = first_fit_decreasing(shipments, vehicles)

    return {"algorithm": "milp_pulp", "routes": routes, "unassigned": unassigned}


def save_routes(routes: List[dict], conn):
    """Persist optimized routes to DB."""
    with conn.cursor() as cur:
        for r in routes:
            cur.execute(
                """INSERT INTO routes 
                   (route_id, vehicle_id, shipment_ids, total_distance, total_cost, utilization_percent, estimated_co2)
                   VALUES (%s, %s, %s::uuid[], %s, %s, %s, %s)
                   ON CONFLICT (route_id) DO NOTHING""",
                (
                    r["route_id"],
                    r["vehicle_id"],
                    "{" + ",".join(r["shipment_ids"]) + "}",
                    r["total_distance_km"],
                    r["total_cost_inr"],
                    r["utilization_percent"],
                    r["estimated_co2_kg"],
                ),
            )
            # Update shipment status
            if r["shipment_ids"]:
                cur.execute(
                    "UPDATE shipments SET status='optimized' WHERE shipment_id = ANY(%s::uuid[])",
                    ("{" + ",".join(r["shipment_ids"]) + "}",),
                )


# ── Routes ─────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "service": "optimization-service"}


@app.get("/metrics")
async def metrics_endpoint():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/api/optimize")
async def run_optimization(algorithm: str = "vrp", use_cache: bool = True):
    """Run load optimization. algorithm='vrp' | 'milp' | 'ffd'"""
    cache_key = f"optimization:result:{algorithm}"
    if use_cache:
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)

    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM shipments WHERE status='pending' OR status='optimized' ORDER BY priority DESC, created_at DESC LIMIT 200")
            shipment_rows = cur.fetchall()
            cur.execute("SELECT * FROM vehicles WHERE availability_status=TRUE LIMIT 50")
            vehicle_rows = cur.fetchall()

        shipments = [dict(r) for r in shipment_rows]
        vehicles = [dict(r) for r in vehicle_rows]

        for s in shipments:
            for k, v in s.items():
                if isinstance(v, uuid.UUID):
                    s[k] = str(v)
        for v in vehicles:
            for k, val in v.items():
                if isinstance(val, uuid.UUID):
                    v[k] = str(val)

        if not shipments:
            return {"message": "No shipments to optimize", "routes": []}
        if not vehicles:
            return {"message": "No vehicles available", "routes": []}

        with opt_duration.time():
            if algorithm == "milp":
                result = run_milp_pulp(shipments, vehicles)
            elif algorithm == "ffd":
                routes, unassigned = first_fit_decreasing(shipments, vehicles)
                result = {"algorithm": "ffd", "routes": routes, "unassigned": unassigned}
            else:
                result = run_vrp_ortools(shipments, vehicles)

        routes = result["routes"]
        save_routes(routes, conn)
        conn.commit()

        # Summary stats
        total_distance = sum(r["total_distance_km"] for r in routes)
        total_cost = sum(r["total_cost_inr"] for r in routes)
        total_co2 = sum(r["estimated_co2_kg"] for r in routes)
        avg_utilization = np.mean([r["utilization_percent"] for r in routes]) if routes else 0
        num_shipments_optimized = sum(r["num_shipments"] for r in routes)

        # Baseline (no consolidation) estimates
        baseline_trips = len(shipments)
        trips_saved = baseline_trips - len(routes)
        baseline_cost = sum(
            haversine(s["origin_lat"], s["origin_lng"], s["destination_lat"], s["destination_lng"])
            * (vehicles[0]["cost_per_km"] if vehicles else 15)
            for s in shipments
        )
        cost_savings = max(0, baseline_cost - total_cost)

        summary = {
            "algorithm": result["algorithm"],
            "num_routes": len(routes),
            "num_shipments_optimized": num_shipments_optimized,
            "unassigned_count": len(result.get("unassigned", [])),
            "total_distance_km": round(total_distance, 2),
            "total_cost_inr": round(total_cost, 2),
            "total_co2_kg": round(total_co2, 2),
            "avg_utilization_percent": round(float(avg_utilization), 2),
            "trips_saved": max(0, trips_saved),
            "cost_savings_inr": round(cost_savings, 2),
            "routes": routes,
        }

        redis_client.setex(cache_key, 120, json.dumps(summary))
        optimization_runs.labels(algorithm=algorithm).inc()
        logger.info(f"Optimization complete: {len(routes)} routes, {num_shipments_optimized} shipments")
        return summary

    except Exception as e:
        conn.rollback()
        logger.error(f"Optimization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.get("/api/routes")
async def list_routes(limit: int = 50):
    """List optimized routes."""
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM routes ORDER BY created_at DESC LIMIT %s", (limit,))
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


@app.get("/api/carbon/report")
async def carbon_report():
    """Get carbon emissions report."""
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT SUM(estimated_co2) as total_co2, COUNT(*) as total_routes, AVG(utilization_percent) as avg_util FROM routes")
            row = cur.fetchone()
            total_co2 = float(row["total_co2"] or 0)
            # Estimated baseline (individual trips, avg 200km each)
            cur.execute("SELECT COUNT(*) as total FROM shipments")
            ship_count = cur.fetchone()["total"]
            baseline_co2 = ship_count * 200 * settings.emission_factor / 8  # assume 8km/l
            co2_saved = max(0, baseline_co2 - total_co2)
            return {
                "total_co2_kg": round(total_co2, 2),
                "baseline_co2_kg": round(baseline_co2, 2),
                "co2_saved_kg": round(co2_saved, 2),
                "co2_reduction_percent": round((co2_saved / baseline_co2 * 100) if baseline_co2 > 0 else 0, 1),
                "trees_equivalent": round(co2_saved / 21.77, 1),  # avg tree absorbs 21.77kg CO2/year
                "total_routes": int(row["total_routes"] or 0),
                "avg_utilization_percent": round(float(row["avg_util"] or 0), 1),
            }
    finally:
        conn.close()
