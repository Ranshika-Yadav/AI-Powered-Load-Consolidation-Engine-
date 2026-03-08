"""
Shared pytest fixtures and configuration for OptiLoad AI tests.
"""
import pytest
from datetime import datetime, timedelta


@pytest.fixture
def sample_shipments():
    """Generate a list of sample shipments for testing."""
    cities = [
        ("Mumbai", 19.076, 72.878),
        ("Delhi", 28.704, 77.103),
        ("Bangalore", 12.972, 77.595),
        ("Chennai", 13.083, 80.271),
        ("Hyderabad", 17.385, 78.487),
        ("Pune", 18.520, 73.856),
    ]
    shipments = []
    base = datetime(2026, 3, 10, 8, 0)
    for i, (city, lat, lng) in enumerate(cities):
        dest_city, d_lat, d_lng = cities[(i + 2) % len(cities)]
        shipments.append({
            "shipment_id": f"ship-{i:03d}",
            "origin_lat": lat, "origin_lng": lng,
            "destination_lat": d_lat, "destination_lng": d_lng,
            "origin_city": city, "destination_city": dest_city,
            "weight": 1000.0 + i * 500,
            "volume": 5.0 + i * 2,
            "pickup_time": base + timedelta(hours=i * 4),
            "delivery_deadline": base + timedelta(hours=48 + i * 4),
            "priority": (i % 5) + 1,
            "status": "pending",
            "cargo_type": "general",
        })
    return shipments


@pytest.fixture
def sample_vehicles():
    """Generate a list of sample vehicles for testing."""
    return [
        {
            "vehicle_id": f"veh-{i:02d}",
            "vehicle_type": "large_truck",
            "capacity_weight": 15000,
            "capacity_volume": 60.0,
            "cost_per_km": 15.0,
            "fuel_efficiency": 8.0,
            "co2_per_km": 0.92,
            "availability_status": True,
            "current_lat": 19.076 + i * 0.1,
            "current_lng": 72.878 + i * 0.1,
            "current_city": "Mumbai",
        }
        for i in range(5)
    ]
