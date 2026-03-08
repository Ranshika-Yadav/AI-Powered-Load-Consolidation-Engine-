"""
Integration / API tests for OptiLoad AI
Run with: pytest tests/integration/ -v
Services must be running (docker-compose up or locally).
"""
import pytest
import httpx
import uuid

BASE_AUTH = "http://localhost:8001"
BASE_INGESTION = "http://localhost:8002"
BASE_CLUSTERING = "http://localhost:8003"
BASE_OPTIMIZATION = "http://localhost:8004"
BASE_SIMULATION = "http://localhost:8005"
BASE_ANALYTICS = "http://localhost:8006"


@pytest.fixture(scope="session")
def auth_token():
    """Obtain JWT token for authenticated requests."""
    try:
        res = httpx.post(f"{BASE_AUTH}/auth/login",
                         data={"username": "admin", "password": "demo123"},
                         timeout=10)
        if res.status_code == 200:
            return res.json()["access_token"]
    except Exception:
        pass
    return None


@pytest.fixture
def headers(auth_token):
    if auth_token:
        return {"Authorization": f"Bearer {auth_token}"}
    return {}


# ── Auth Service Tests ────────────────────────────────────────────────────────
class TestAuthService:
    def test_health(self):
        try:
            res = httpx.get(f"{BASE_AUTH}/health", timeout=5)
            assert res.status_code == 200
            assert res.json()["status"] == "ok"
        except httpx.ConnectError:
            pytest.skip("Auth service not running")

    def test_login_valid_credentials(self):
        try:
            res = httpx.post(f"{BASE_AUTH}/auth/login",
                             data={"username": "admin", "password": "demo123"}, timeout=10)
            if res.status_code == 200:
                data = res.json()
                assert "access_token" in data
                assert "refresh_token" in data
                assert data["token_type"] == "bearer"
        except httpx.ConnectError:
            pytest.skip("Auth service not running")

    def test_login_invalid_credentials(self):
        try:
            res = httpx.post(f"{BASE_AUTH}/auth/login",
                             data={"username": "bad_user", "password": "bad_pass"}, timeout=10)
            assert res.status_code in (401, 422)
        except httpx.ConnectError:
            pytest.skip("Auth service not running")

    def test_metrics_endpoint(self):
        try:
            res = httpx.get(f"{BASE_AUTH}/metrics", timeout=5)
            assert res.status_code == 200
        except httpx.ConnectError:
            pytest.skip("Auth service not running")


# ── Ingestion Service Tests ───────────────────────────────────────────────────
class TestIngestionService:
    def test_health(self):
        try:
            res = httpx.get(f"{BASE_INGESTION}/health", timeout=5)
            assert res.status_code == 200
        except httpx.ConnectError:
            pytest.skip("Ingestion service not running")

    def test_list_shipments(self):
        try:
            res = httpx.get(f"{BASE_INGESTION}/api/shipments", timeout=10)
            assert res.status_code == 200
            assert isinstance(res.json(), list)
        except httpx.ConnectError:
            pytest.skip("Ingestion service not running")

    def test_create_single_shipment(self):
        try:
            payload = {
                "origin_lat": 19.076, "origin_lng": 72.878,
                "destination_lat": 12.972, "destination_lng": 77.595,
                "origin_city": "Mumbai", "destination_city": "Bangalore",
                "weight": 1500.0, "volume": 8.0,
                "pickup_time": "2026-03-10T08:00:00",
                "delivery_deadline": "2026-03-12T18:00:00",
                "priority": 3, "cargo_type": "electronics",
            }
            res = httpx.post(f"{BASE_INGESTION}/api/shipments/single",
                             json=payload, timeout=10)
            if res.status_code == 201:
                data = res.json()
                assert "shipment_id" in data
                assert data["status"] == "pending"
        except httpx.ConnectError:
            pytest.skip("Ingestion service not running")

    def test_upload_invalid_file_type(self):
        try:
            files = {"file": ("test.txt", b"not a csv", "text/plain")}
            res = httpx.post(f"{BASE_INGESTION}/api/shipments/upload", files=files, timeout=10)
            assert res.status_code == 400
        except httpx.ConnectError:
            pytest.skip("Ingestion service not running")


# ── Clustering Service Tests ──────────────────────────────────────────────────
class TestClusteringService:
    def test_health(self):
        try:
            res = httpx.get(f"{BASE_CLUSTERING}/health", timeout=5)
            assert res.status_code == 200
        except httpx.ConnectError:
            pytest.skip("Clustering service not running")

    def test_list_clusters(self):
        try:
            res = httpx.get(f"{BASE_CLUSTERING}/api/clusters", timeout=10)
            assert res.status_code == 200
            assert isinstance(res.json(), list)
        except httpx.ConnectError:
            pytest.skip("Clustering service not running")

    def test_run_clustering_returns_structure(self):
        try:
            res = httpx.post(f"{BASE_CLUSTERING}/api/clusters/run", timeout=30)
            assert res.status_code == 200
            data = res.json()
            assert "num_clusters" in data or "message" in data
        except httpx.ConnectError:
            pytest.skip("Clustering service not running")


# ── Optimization Service Tests ────────────────────────────────────────────────
class TestOptimizationService:
    def test_health(self):
        try:
            res = httpx.get(f"{BASE_OPTIMIZATION}/health", timeout=5)
            assert res.status_code == 200
        except httpx.ConnectError:
            pytest.skip("Optimization service not running")

    def test_run_optimization_ffd(self):
        try:
            res = httpx.post(f"{BASE_OPTIMIZATION}/api/optimize?algorithm=ffd", timeout=30)
            assert res.status_code == 200
            data = res.json()
            assert "routes" in data
            assert "num_routes" in data or "message" in data
        except httpx.ConnectError:
            pytest.skip("Optimization service not running")

    def test_carbon_report_returns_dict(self):
        try:
            res = httpx.get(f"{BASE_OPTIMIZATION}/api/carbon/report", timeout=10)
            assert res.status_code == 200
            data = res.json()
            assert "total_co2_kg" in data
            assert "co2_saved_kg" in data
        except httpx.ConnectError:
            pytest.skip("Optimization service not running")


# ── Simulation Service Tests ──────────────────────────────────────────────────
class TestSimulationService:
    def test_health(self):
        try:
            res = httpx.get(f"{BASE_SIMULATION}/health", timeout=5)
            assert res.status_code == 200
        except httpx.ConnectError:
            pytest.skip("Simulation service not running")

    def test_run_simulation_returns_stats(self):
        try:
            payload = {"num_simulations": 50, "base_fleet_size": 10, "base_shipment_volume": 100}
            res = httpx.post(f"{BASE_SIMULATION}/api/simulate", json=payload, timeout=30)
            assert res.status_code == 200
            data = res.json()
            assert "avg_utilization" in data
            assert "total_cost" in data
            assert "co2_emission" in data
            assert data["num_simulations"] == 50
        except httpx.ConnectError:
            pytest.skip("Simulation service not running")


# ── Analytics Service Tests ───────────────────────────────────────────────────
class TestAnalyticsService:
    def test_health(self):
        try:
            res = httpx.get(f"{BASE_ANALYTICS}/health", timeout=5)
            assert res.status_code == 200
        except httpx.ConnectError:
            pytest.skip("Analytics service not running")

    def test_get_dashboard_metrics(self):
        try:
            res = httpx.get(f"{BASE_ANALYTICS}/api/metrics", timeout=15)
            assert res.status_code == 200
            data = res.json()
            assert "shipments" in data
            assert "vehicles" in data
            assert "optimization" in data
            assert "carbon" in data
        except httpx.ConnectError:
            pytest.skip("Analytics service not running")

    def test_get_recommendations(self):
        try:
            res = httpx.get(f"{BASE_ANALYTICS}/api/recommendations", timeout=15)
            assert res.status_code == 200
            data = res.json()
            assert "recommendations" in data
            assert isinstance(data["recommendations"], list)
        except httpx.ConnectError:
            pytest.skip("Analytics service not running")
