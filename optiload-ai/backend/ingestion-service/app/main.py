"""
Ingestion Service — OptiLoad AI
Handles shipment uploads, validation, and geospatial normalization
"""
import io
import uuid
import logging
from datetime import datetime
from typing import List, Optional
import math

import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
import redis
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import Response
from pydantic import BaseModel, validator, Field
from pydantic_settings import BaseSettings
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import json
import httpx

# ── Settings ───────────────────────────────────────────────────────────────────
class Settings(BaseSettings):
    database_url: str = "postgresql://optiload:optiload_secret@localhost:5432/optiload_db"
    redis_url: str = "redis://localhost:6379/1"
    rabbitmq_url: str = "amqp://optiload:optiload_rabbit@localhost:5672/"
    auth_service_url: str = "http://localhost:8001"

    class Config:
        env_file = ".env"


settings = Settings()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="OptiLoad AI — Ingestion Service",
    description="Shipment data ingestion, validation, and geospatial normalization",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="http://localhost:8001/auth/login", auto_error=False)
redis_client = redis.from_url(settings.redis_url, decode_responses=True)

# ── Metrics ────────────────────────────────────────────────────────────────────
shipments_ingested = Counter("ingestion_shipments_total", "Shipments ingested", ["status"])
upload_duration = Histogram("ingestion_upload_duration_seconds", "Upload processing time")


# ── DB Helper ──────────────────────────────────────────────────────────────────
def get_db():
    db_url = settings.database_url.replace("postgresql://", "")
    user_pass, rest = db_url.split("@")
    user, password = user_pass.split(":")
    host_db = rest.split("/")
    db = host_db[-1]
    host_port = host_db[0]
    host, port = (host_port.split(":") + ["5432"])[:2]
    return psycopg2.connect(host=host, port=port, dbname=db, user=user, password=password)


# ── Pydantic Models ────────────────────────────────────────────────────────────
class ShipmentCreate(BaseModel):
    origin_lat: float = Field(..., ge=-90, le=90)
    origin_lng: float = Field(..., ge=-180, le=180)
    destination_lat: float = Field(..., ge=-90, le=90)
    destination_lng: float = Field(..., ge=-180, le=180)
    origin_city: Optional[str] = ""
    destination_city: Optional[str] = ""
    weight: float = Field(..., gt=0, le=50000)
    volume: float = Field(..., gt=0, le=200)
    pickup_time: datetime
    delivery_deadline: datetime
    priority: int = Field(1, ge=1, le=5)
    cargo_type: str = "general"
    special_requirements: Optional[str] = None

    @validator("delivery_deadline")
    def deadline_after_pickup(cls, v, values):
        if "pickup_time" in values and v <= values["pickup_time"]:
            raise ValueError("delivery_deadline must be after pickup_time")
        return v

    @validator("origin_lat", "destination_lat")
    def valid_lat(cls, v):
        if not (-90 <= v <= 90):
            raise ValueError("Latitude must be between -90 and 90")
        return v


class VehicleCreate(BaseModel):
    vehicle_type: str
    registration_number: Optional[str] = None
    capacity_weight: float = Field(..., gt=0)
    capacity_volume: float = Field(..., gt=0)
    cost_per_km: float = Field(..., gt=0)
    fuel_efficiency: float = Field(..., gt=0)
    co2_per_km: float = Field(..., gt=0)
    current_lat: Optional[float] = None
    current_lng: Optional[float] = None
    current_city: Optional[str] = None
    driver_name: Optional[str] = None


class ShipmentResponse(BaseModel):
    shipment_id: str
    status: str
    origin_city: Optional[str]
    destination_city: Optional[str]
    weight: float
    volume: float
    priority: int
    created_at: str


class UploadResponse(BaseModel):
    success_count: int
    failed_count: int
    shipment_ids: List[str]
    errors: List[str]


# ── Helpers ────────────────────────────────────────────────────────────────────
def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate Haversine distance in km between two coordinates."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def insert_shipment(cur, s: ShipmentCreate) -> str:
    """Insert a validated shipment into the DB."""
    sid = str(uuid.uuid4())
    cur.execute(
        """INSERT INTO shipments 
           (shipment_id, origin_lat, origin_lng, destination_lat, destination_lng,
            origin_city, destination_city, weight, volume,
            pickup_time, delivery_deadline, priority, cargo_type, special_requirements, status)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending')
           RETURNING shipment_id""",
        (
            sid,
            s.origin_lat, s.origin_lng,
            s.destination_lat, s.destination_lng,
            s.origin_city, s.destination_city,
            s.weight, s.volume,
            s.pickup_time, s.delivery_deadline,
            s.priority, s.cargo_type, s.special_requirements,
        ),
    )
    return sid


def parse_csv_row(row: dict) -> ShipmentCreate:
    """Parse a CSV row dict into a ShipmentCreate model."""
    return ShipmentCreate(
        origin_lat=float(row.get("origin_lat", 0)),
        origin_lng=float(row.get("origin_lng", 0)),
        destination_lat=float(row.get("destination_lat", 0)),
        destination_lng=float(row.get("destination_lng", 0)),
        origin_city=str(row.get("origin_city", "")),
        destination_city=str(row.get("destination_city", "")),
        weight=float(row.get("weight", 1)),
        volume=float(row.get("volume", 1)),
        pickup_time=pd.to_datetime(row.get("pickup_time")),
        delivery_deadline=pd.to_datetime(row.get("delivery_deadline")),
        priority=int(row.get("priority", 1)),
        cargo_type=str(row.get("cargo_type", "general")),
        special_requirements=row.get("special_requirements"),
    )


# ── Routes ─────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "service": "ingestion-service"}


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/api/shipments/upload", response_model=UploadResponse)
async def upload_shipments(file: UploadFile = File(...)):
    """Upload CSV file with shipments. Validates, normalizes, and stores them."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    with upload_duration.time():
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode("utf-8")))

        success_ids, errors = [], []
        conn = get_db()
        try:
            with conn.cursor() as cur:
                for idx, row in df.iterrows():
                    try:
                        shipment = parse_csv_row(row.to_dict())
                        sid = insert_shipment(cur, shipment)
                        success_ids.append(sid)
                        shipments_ingested.labels(status="success").inc()
                    except Exception as e:
                        errors.append(f"Row {idx}: {str(e)}")
                        shipments_ingested.labels(status="failed").inc()
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            conn.close()

    # Invalidate cache
    redis_client.delete("shipments:list", "metrics:summary")
    logger.info(f"Ingested {len(success_ids)} shipments, {len(errors)} errors")

    return UploadResponse(
        success_count=len(success_ids),
        failed_count=len(errors),
        shipment_ids=success_ids,
        errors=errors,
    )


@app.post("/api/shipments/single", response_model=ShipmentResponse, status_code=201)
async def create_single_shipment(shipment: ShipmentCreate):
    """Create a single shipment via JSON payload."""
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sid = insert_shipment(cur, shipment)
            conn.commit()
            cur.execute("SELECT * FROM shipments WHERE shipment_id=%s", (sid,))
            row = cur.fetchone()
            redis_client.delete("shipments:list", "metrics:summary")
            return ShipmentResponse(
                shipment_id=str(row["shipment_id"]),
                status=row["status"],
                origin_city=row.get("origin_city"),
                destination_city=row.get("destination_city"),
                weight=row["weight"],
                volume=row["volume"],
                priority=row["priority"],
                created_at=str(row["created_at"]),
            )
    finally:
        conn.close()


@app.get("/api/shipments")
async def list_shipments(limit: int = 100, offset: int = 0, status: str = None):
    """List all shipments with optional status filter. Results cached in Redis."""
    cache_key = f"shipments:list:{status}:{limit}:{offset}"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if status:
                cur.execute("SELECT * FROM shipments WHERE status=%s ORDER BY created_at DESC LIMIT %s OFFSET %s",
                            (status, limit, offset))
            else:
                cur.execute("SELECT * FROM shipments ORDER BY created_at DESC LIMIT %s OFFSET %s", (limit, offset))
            rows = cur.fetchall()
            result = [dict(r) for r in rows]
            for r in result:
                for k, v in r.items():
                    if isinstance(v, uuid.UUID):
                        r[k] = str(v)
                    elif isinstance(v, datetime):
                        r[k] = v.isoformat()
            redis_client.setex(cache_key, 30, json.dumps(result))
            return result
    finally:
        conn.close()


@app.get("/api/shipments/{shipment_id}")
async def get_shipment(shipment_id: str):
    """Get a specific shipment by ID."""
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM shipments WHERE shipment_id=%s", (shipment_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Shipment not found")
            result = dict(row)
            for k, v in result.items():
                if isinstance(v, uuid.UUID):
                    result[k] = str(v)
                elif isinstance(v, datetime):
                    result[k] = v.isoformat()
            return result
    finally:
        conn.close()


@app.post("/api/vehicles/bulk")
async def bulk_upload_vehicles(file: UploadFile = File(...)):
    """Upload vehicles via CSV."""
    contents = await file.read()
    df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
    success, errors = 0, []
    conn = get_db()
    try:
        with conn.cursor() as cur:
            for idx, row in df.iterrows():
                try:
                    vid = str(uuid.uuid4())
                    cur.execute(
                        """INSERT INTO vehicles
                           (vehicle_id, vehicle_type, registration_number, capacity_weight, capacity_volume,
                            cost_per_km, fuel_efficiency, co2_per_km, current_lat, current_lng, current_city, driver_name)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (
                            vid,
                            row.get("vehicle_type", "truck"),
                            row.get("registration_number"),
                            float(row.get("capacity_weight", 10000)),
                            float(row.get("capacity_volume", 50)),
                            float(row.get("cost_per_km", 15)),
                            float(row.get("fuel_efficiency", 8)),
                            float(row.get("co2_per_km", 0.9)),
                            float(row.get("current_lat", 0)) if row.get("current_lat") else None,
                            float(row.get("current_lng", 0)) if row.get("current_lng") else None,
                            row.get("current_city"),
                            row.get("driver_name"),
                        ),
                    )
                    success += 1
                except Exception as e:
                    errors.append(f"Row {idx}: {str(e)}")
            conn.commit()
    finally:
        conn.close()
    return {"success_count": success, "failed_count": len(errors), "errors": errors}


@app.get("/api/vehicles")
async def list_vehicles():
    """List all vehicles."""
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM vehicles ORDER BY created_at DESC")
            rows = cur.fetchall()
            result = []
            for r in rows:
                d = dict(r)
                for k, v in d.items():
                    if isinstance(v, uuid.UUID):
                        d[k] = str(v)
                    elif isinstance(v, datetime):
                        d[k] = v.isoformat()
                result.append(d)
            return result
    finally:
        conn.close()


@app.post("/api/demo/load")
async def load_demo_data():
    """Load the synthetic demo dataset from data/demo_dataset/."""
    import os
    demo_dir = "/app/data/demo_dataset"
    if not os.path.exists(demo_dir):
        raise HTTPException(status_code=404, detail="Demo dataset not found. Run demo generator first.")

    results = {}
    # Load shipments
    ship_path = os.path.join(demo_dir, "shipments.csv")
    if os.path.exists(ship_path):
        with open(ship_path, "rb") as f:
            class FakeFile:
                filename = "shipments.csv"
                async def read(self):
                    return f.read()
            fake = FakeFile()
            result = await upload_shipments(fake)
            results["shipments"] = result

    # Load vehicles
    veh_path = os.path.join(demo_dir, "vehicles.csv")
    if os.path.exists(veh_path):
        with open(veh_path, "rb") as f:
            class FakeFile2:
                filename = "vehicles.csv"
                async def read(self):
                    return f.read()
            fake2 = FakeFile2()
            result2 = await bulk_upload_vehicles(fake2)
            results["vehicles"] = result2

    return results
