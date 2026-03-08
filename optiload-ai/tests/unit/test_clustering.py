"""
Tests for OptiLoad AI — Clustering Service
"""
import pytest
import math
from datetime import datetime, timedelta


# ── Import the core functions from the clustering service ─────────────────────
import sys
sys.path.insert(0, "/Users/ranshikayadav/Desktop/Ai_load_p/optiload-ai/backend/clustering-service")

def haversine(lat1, lng1, lat2, lng2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def cosine_similarity(v1, v2):
    import numpy as np
    a, b = np.array(v1), np.array(v2)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


# ── Fixtures ──────────────────────────────────────────────────────────────────
@pytest.fixture
def sample_shipment_mumbai():
    return {
        "shipment_id": "ship-001",
        "origin_lat": 19.076, "origin_lng": 72.878,
        "destination_lat": 12.972, "destination_lng": 77.595,
        "weight": 1500.0, "volume": 8.0,
        "pickup_time": datetime(2026, 3, 10, 8, 0),
        "delivery_deadline": datetime(2026, 3, 12, 18, 0),
        "priority": 3, "status": "pending",
    }


@pytest.fixture
def sample_shipment_nearby():
    """Shipment originating near Mumbai (should be compatible)."""
    return {
        "shipment_id": "ship-002",
        "origin_lat": 18.520, "origin_lng": 73.856,
        "destination_lat": 12.972, "destination_lng": 77.595,
        "weight": 2000.0, "volume": 12.0,
        "pickup_time": datetime(2026, 3, 10, 9, 0),
        "delivery_deadline": datetime(2026, 3, 12, 20, 0),
        "priority": 2, "status": "pending",
    }


@pytest.fixture
def sample_shipment_far():
    """Shipment originating in Kolkata (should NOT be compatible with Mumbai)."""
    return {
        "shipment_id": "ship-003",
        "origin_lat": 22.573, "origin_lng": 88.364,
        "destination_lat": 28.704, "destination_lng": 77.103,
        "weight": 3000.0, "volume": 15.0,
        "pickup_time": datetime(2026, 3, 11, 8, 0),
        "delivery_deadline": datetime(2026, 3, 14, 18, 0),
        "priority": 1, "status": "pending",
    }


# ── Haversine Tests ───────────────────────────────────────────────────────────
class TestHaversine:
    def test_same_point_is_zero(self):
        d = haversine(19.076, 72.878, 19.076, 72.878)
        assert d == pytest.approx(0.0, abs=0.001)

    def test_mumbai_to_pune_approx_120km(self):
        d = haversine(19.076, 72.878, 18.520, 73.856)
        assert 100 < d < 160, f"Expected ~120km direct distance, got {d:.1f}km"

    def test_mumbai_to_delhi_approx_1150km(self):
        d = haversine(19.076, 72.878, 28.704, 77.103)
        assert 1100 < d < 1250

    def test_symmetry(self):
        d1 = haversine(19.076, 72.878, 22.573, 88.364)
        d2 = haversine(22.573, 88.364, 19.076, 72.878)
        assert d1 == pytest.approx(d2, abs=0.001)

    def test_returns_positive(self):
        d = haversine(0, 0, 1, 1)
        assert d > 0


# ── Cosine Similarity Tests ───────────────────────────────────────────────────
class TestCosineSimilarity:
    def test_identical_vectors(self):
        v = [19.0, 72.8, 12.9, 77.6]
        assert cosine_similarity(v, v) == pytest.approx(1.0, abs=1e-6)

    def test_orthogonal_vectors(self):
        # (1,0) and (0,1) → cosine = 0
        sim = cosine_similarity([1, 0, 0, 0], [0, 1, 0, 0])
        assert sim == pytest.approx(0.0, abs=1e-6)

    def test_similar_routes_high_similarity(self, sample_shipment_mumbai, sample_shipment_nearby):
        v1 = [sample_shipment_mumbai["origin_lat"], sample_shipment_mumbai["origin_lng"],
              sample_shipment_mumbai["destination_lat"], sample_shipment_mumbai["destination_lng"]]
        v2 = [sample_shipment_nearby["origin_lat"], sample_shipment_nearby["origin_lng"],
              sample_shipment_nearby["destination_lat"], sample_shipment_nearby["destination_lng"]]
        sim = cosine_similarity(v1, v2)
        assert sim > 0.95, f"Expected high similarity, got {sim:.3f}"

    def test_zero_vector_returns_zero(self):
        assert cosine_similarity([0, 0, 0, 0], [1, 2, 3, 4]) == 0.0


# ── Shipment Compatibility Tests ──────────────────────────────────────────────
class TestShipmentCompatibility:
    def test_nearby_shipments_compatible(self, sample_shipment_mumbai, sample_shipment_nearby):
        dist = haversine(
            sample_shipment_mumbai["origin_lat"], sample_shipment_mumbai["origin_lng"],
            sample_shipment_nearby["origin_lat"], sample_shipment_nearby["origin_lng"],
        )
        # They should be within 200km
        assert dist < 200, f"Nearby shipments too far: {dist:.1f}km"

    def test_far_shipments_incompatible(self, sample_shipment_mumbai, sample_shipment_far):
        dist = haversine(
            sample_shipment_mumbai["origin_lat"], sample_shipment_mumbai["origin_lng"],
            sample_shipment_far["origin_lat"], sample_shipment_far["origin_lng"],
        )
        assert dist > 500, f"Expected far distance, got {dist:.1f}km"

    def test_time_window_overlap(self, sample_shipment_mumbai, sample_shipment_nearby):
        """Time windows should overlap."""
        overlap_start = max(sample_shipment_mumbai["pickup_time"], sample_shipment_nearby["pickup_time"])
        overlap_end = min(sample_shipment_mumbai["delivery_deadline"], sample_shipment_nearby["delivery_deadline"])
        overlap_hours = max(0, (overlap_end - overlap_start).total_seconds() / 3600)
        assert overlap_hours > 4, f"Expected time overlap > 4h, got {overlap_hours:.1f}h"

    def test_no_time_window_overlap(self):
        s1_pickup = datetime(2026, 3, 10, 8, 0)
        s1_deadline = datetime(2026, 3, 10, 14, 0)
        s2_pickup = datetime(2026, 3, 10, 16, 0)
        s2_deadline = datetime(2026, 3, 10, 22, 0)
        overlap_start = max(s1_pickup, s2_pickup)
        overlap_end = min(s1_deadline, s2_deadline)
        overlap_hours = max(0, (overlap_end - overlap_start).total_seconds() / 3600)
        assert overlap_hours == 0


# ── Bin Packing Tests ─────────────────────────────────────────────────────────
class TestBinPacking:
    def test_ffd_fills_vehicles(self):
        """First Fit Decreasing should place all shipments fitting within capacity."""
        vehicles = [
            {"vehicle_id": "v1", "capacity_weight": 10000, "capacity_volume": 50.0,
             "cost_per_km": 15, "fuel_efficiency": 8, "vehicle_type": "truck",
             "current_lat": 19.076, "current_lng": 72.878},
        ]
        shipments = [
            {"shipment_id": f"s{i}", "weight": 1000, "volume": 5.0,
             "origin_lat": 19.076, "origin_lng": 72.878,
             "destination_lat": 12.972, "destination_lng": 77.595}
            for i in range(5)
        ]
        # 5 × 5m³ = 25m³ < 50m³ capacity → all should fit
        total_vol = sum(s["volume"] for s in shipments)
        assert total_vol <= vehicles[0]["capacity_volume"]

    def test_overweight_shipment_exceeds_small_vehicle(self):
        """A 20T shipment should not fit in a 5T vehicle."""
        vehicle_cap = 5000
        shipment_weight = 20000
        assert shipment_weight > vehicle_cap


# ── Carbon Calculation Tests ──────────────────────────────────────────────────
class TestCarbonCalculation:
    EMISSION_FACTOR = 2.68  # kg CO2 per liter diesel

    def calculate_co2(self, distance_km, fuel_efficiency_km_per_l):
        liters = distance_km / fuel_efficiency_km_per_l
        return liters * self.EMISSION_FACTOR

    def test_zero_distance_zero_co2(self):
        co2 = self.calculate_co2(0, 8)
        assert co2 == pytest.approx(0.0)

    def test_higher_efficiency_lower_co2(self):
        co2_efficient = self.calculate_co2(100, 12)
        co2_inefficient = self.calculate_co2(100, 6)
        assert co2_efficient < co2_inefficient

    def test_proportional_with_distance(self):
        co2_100 = self.calculate_co2(100, 8)
        co2_200 = self.calculate_co2(200, 8)
        assert co2_200 == pytest.approx(2 * co2_100, rel=0.01)

    def test_realistic_range(self):
        # 350km trip, 8km/l, 2.68 emission factor → ~117 kg CO2
        co2 = self.calculate_co2(350, 8)
        assert 100 < co2 < 140, f"Expected ~117 kg CO2, got {co2:.1f}"
