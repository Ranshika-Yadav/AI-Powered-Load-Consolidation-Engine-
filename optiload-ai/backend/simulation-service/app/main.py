"""
Simulation Service — OptiLoad AI
Monte Carlo simulation engine for logistics scenario analysis
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
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import json

class Settings(BaseSettings):
    database_url: str = "postgresql://optiload:optiload_secret@localhost:5432/optiload_db"
    redis_url: str = "redis://localhost:6379/4"
    rabbitmq_url: str = "amqp://optiload:optiload_rabbit@localhost:5672/"
    class Config:
        env_file = ".env"

settings = Settings()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="OptiLoad AI — Simulation Service",
    description="Monte Carlo scenario simulation engine",
    version="1.0.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
redis_client = redis.from_url(settings.redis_url, decode_responses=True)
sim_runs = Counter("simulation_runs_total", "Simulation runs")
sim_duration = Histogram("simulation_duration_seconds", "Simulation duration")


def get_db():
    db_url = settings.database_url.replace("postgresql://", "")
    user_pass, rest = db_url.split("@")
    user, password = user_pass.split(":")
    host_db = rest.split("/")
    db = host_db[-1]
    host_port = host_db[0]
    host, port = (host_port.split(":") + ["5432"])[:2]
    return psycopg2.connect(host=host, port=port, dbname=db, user=user, password=password)


class SimulationRequest(BaseModel):
    num_simulations: int = Field(200, ge=50, le=1000)
    base_fleet_size: int = Field(20, ge=1, le=100)
    base_shipment_volume: int = Field(200, ge=10, le=1000)
    simulation_name: str = "Monte Carlo Run"
    # Variance parameters
    fleet_size_std: float = Field(3.0, ge=0)
    shipment_volume_std: float = Field(20.0, ge=0)
    traffic_delay_mean: float = Field(1.2, ge=1.0)  # multiplier
    traffic_delay_std: float = Field(0.15, ge=0)
    fuel_cost_base: float = Field(92.0, ge=0)       # INR per liter
    fuel_cost_std: float = Field(5.0, ge=0)
    avg_distance_km: float = Field(350.0, ge=0)
    avg_vehicle_capacity: float = Field(20.0, ge=0)
    cost_per_km_base: float = Field(15.0, ge=0)
    emission_factor: float = Field(2.68, ge=0)
    fuel_efficiency_base: float = Field(8.0, ge=0)  # km/l


class SimulationScenario(BaseModel):
    fleet_size: Optional[int] = None
    shipment_volume: Optional[int] = None
    delivery_window_hours: Optional[float] = None
    consolidation_threshold: Optional[float] = None
    num_simulations: int = Field(300, ge=50, le=1000)
    simulation_name: str = "Scenario Analysis"


def run_single_simulation(params: Dict) -> Dict:
    """Run one Monte Carlo iteration."""
    fleet_size = max(1, int(np.random.normal(params["fleet_size"], params["fleet_size_std"])))
    shipment_vol = max(1, int(np.random.normal(params["shipment_volume"], params["shipment_volume_std"])))
    traffic_mult = max(1.0, np.random.normal(params["traffic_delay_mean"], params["traffic_delay_std"]))
    fuel_cost = max(50, np.random.normal(params["fuel_cost_base"], params["fuel_cost_std"]))

    # Consolidation efficiency: more fleet → better utilization
    raw_trips = shipment_vol  # without consolidation
    # Consolidation reduces trips
    avg_shipments_per_vehicle = max(1, shipment_vol / fleet_size)
    consolidation_factor = min(0.85, 0.4 + 0.015 * avg_shipments_per_vehicle)
    trips = max(fleet_size, int(raw_trips * (1 - consolidation_factor)))
    trips_saved = raw_trips - trips

    avg_utilization = min(99.0, max(10.0, 
        (shipment_vol / (fleet_size * (params.get("avg_vehicle_capacity", 20) or 20))) * 100
    ))
    
    total_distance = trips * params["avg_distance_km"] * traffic_mult
    fuel_usage = total_distance / params["fuel_efficiency_base"]
    fuel_price_cost = fuel_usage * fuel_cost
    operating_cost = total_distance * params["cost_per_km_base"]
    total_cost = operating_cost + fuel_price_cost * 0.3  # fuel is part of cost_per_km
    co2_emission = fuel_usage * params["emission_factor"]

    return {
        "fleet_size": fleet_size,
        "shipment_volume": shipment_vol,
        "trips": trips,
        "trips_saved": trips_saved,
        "avg_utilization": avg_utilization,
        "total_cost": total_cost,
        "fuel_usage": fuel_usage,
        "co2_emission": co2_emission,
        "traffic_multiplier": traffic_mult,
        "fuel_cost_per_l": fuel_cost,
    }


def monte_carlo_simulate(request: SimulationRequest) -> Dict:
    """Run full Monte Carlo simulation."""
    params = {
        "fleet_size": request.base_fleet_size,
        "fleet_size_std": request.fleet_size_std,
        "shipment_volume": request.base_shipment_volume,
        "shipment_volume_std": request.shipment_volume_std,
        "traffic_delay_mean": request.traffic_delay_mean,
        "traffic_delay_std": request.traffic_delay_std,
        "fuel_cost_base": request.fuel_cost_base,
        "fuel_cost_std": request.fuel_cost_std,
        "avg_distance_km": request.avg_distance_km,
        "avg_vehicle_capacity": request.avg_vehicle_capacity,
        "cost_per_km_base": request.cost_per_km_base,
        "emission_factor": request.emission_factor,
        "fuel_efficiency_base": request.fuel_efficiency_base,
    }

    np.random.seed(42)
    results = [run_single_simulation(params) for _ in range(request.num_simulations)]

    utilizations = np.array([r["avg_utilization"] for r in results])
    costs = np.array([r["total_cost"] for r in results])
    fuels = np.array([r["fuel_usage"] for r in results])
    co2s = np.array([r["co2_emission"] for r in results])
    trips_arr = np.array([r["trips"] for r in results])
    trips_saved_arr = np.array([r["trips_saved"] for r in results])

    # Baseline (no optimization)
    baseline_trips = request.base_shipment_volume
    baseline_distance = baseline_trips * request.avg_distance_km
    baseline_cost = baseline_distance * request.cost_per_km_base
    baseline_co2 = (baseline_distance / request.fuel_efficiency_base) * request.emission_factor

    avg_cost = float(np.mean(costs))
    avg_co2 = float(np.mean(co2s))

    return {
        "simulation_name": request.simulation_name,
        "num_simulations": request.num_simulations,
        "fleet_size": request.base_fleet_size,
        "shipment_volume": request.base_shipment_volume,
        "avg_utilization": round(float(np.mean(utilizations)), 2),
        "std_utilization": round(float(np.std(utilizations)), 2),
        "avg_trips": round(float(np.mean(trips_arr)), 1),
        "avg_trips_saved": round(float(np.mean(trips_saved_arr)), 1),
        "total_cost": round(avg_cost, 2),
        "std_cost": round(float(np.std(costs)), 2),
        "fuel_usage": round(float(np.mean(fuels)), 2),
        "co2_emission": round(avg_co2, 2),
        "cost_savings": round(max(0, baseline_cost - avg_cost), 2),
        "co2_savings": round(max(0, baseline_co2 - avg_co2), 2),
        "percentile_5_cost": round(float(np.percentile(costs, 5)), 2),
        "percentile_95_cost": round(float(np.percentile(costs, 95)), 2),
        "percentile_5_utilization": round(float(np.percentile(utilizations, 5)), 2),
        "percentile_95_utilization": round(float(np.percentile(utilizations, 95)), 2),
        "baseline_cost": round(baseline_cost, 2),
        "baseline_co2": round(baseline_co2, 2),
        "histogram_costs": [round(float(c), 2) for c in costs[:100]],
        "histogram_utilizations": [round(float(u), 2) for u in utilizations[:100]],
    }


@app.get("/health")
async def health():
    return {"status": "ok", "service": "simulation-service"}


@app.get("/metrics")
async def metrics_endpoint():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/api/simulate")
async def run_simulation(request: SimulationRequest):
    """Run Monte Carlo simulation."""
    cache_key = f"simulation:{request.base_fleet_size}:{request.base_shipment_volume}:{request.num_simulations}"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    with sim_duration.time():
        result = monte_carlo_simulate(request)

    # Persist to DB
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO simulation_results
                   (sim_id, simulation_name, num_simulations, fleet_size, shipment_volume,
                    avg_utilization, total_cost, fuel_usage, co2_emission, trip_count,
                    cost_savings, co2_savings, percentile_5_cost, percentile_95_cost, raw_results)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    str(uuid.uuid4()),
                    result["simulation_name"],
                    result["num_simulations"],
                    result["fleet_size"],
                    result["shipment_volume"],
                    result["avg_utilization"],
                    result["total_cost"],
                    result["fuel_usage"],
                    result["co2_emission"],
                    result["avg_trips"],
                    result["cost_savings"],
                    result["co2_savings"],
                    result["percentile_5_cost"],
                    result["percentile_95_cost"],
                    json.dumps(result),
                ),
            )
            conn.commit()
    except Exception as e:
        conn.rollback()
        logger.warning(f"Could not save simulation: {e}")
    finally:
        conn.close()

    redis_client.setex(cache_key, 300, json.dumps(result))
    sim_runs.inc()
    logger.info(f"Simulation complete: {result['num_simulations']} runs")
    return result


@app.post("/api/simulate/scenario")
async def run_scenario(scenario: SimulationScenario):
    """Run named scenario simulation for comparison."""
    req = SimulationRequest(
        num_simulations=scenario.num_simulations,
        base_fleet_size=scenario.fleet_size or 20,
        base_shipment_volume=scenario.shipment_volume or 200,
        simulation_name=scenario.simulation_name,
    )
    return await run_simulation(req)


@app.get("/api/simulate/history")
async def get_simulation_history(limit: int = 20):
    """Get past simulation results."""
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM simulation_results ORDER BY created_at DESC LIMIT %s", (limit,))
            rows = cur.fetchall()
            result = []
            for r in rows:
                d = dict(r)
                for k, v in d.items():
                    if isinstance(v, uuid.UUID):
                        d[k] = str(v)
                    elif isinstance(v, datetime):
                        d[k] = v.isoformat()
                    elif k == "raw_results" and isinstance(v, str):
                        try:
                            d[k] = json.loads(v)
                        except:
                            pass
                result.append(d)
            return result
    finally:
        conn.close()
