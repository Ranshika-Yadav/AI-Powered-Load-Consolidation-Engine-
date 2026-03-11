# OptiLoad AI 🚛

**Production-Grade AI Logistics Optimization Platform**

> A fully modular microservices system that consolidates shipments, optimizes fleet utilization, reduces transportation costs and carbon emissions — deployable with a single command.

---

## 🚀 Quick Start

```bash
# Clone / navigate to the project
cd optiload-ai

# Start all services
docker-compose up --build

# Access the dashboard
open http://localhost:3000          # Frontend Dashboard
open http://localhost:9090          # Prometheus
open http://localhost:3001          # Grafana (admin/admin)
```

Wait ~60-90 seconds for all services to be healthy, then:

1. Open **http://localhost:3000** and log in with `admin / demo123`
2. Click **"Load Demo Data"** to load 200 synthetic shipments + 20 vehicles
3. Navigate to **Optimize** → Run Clustering → Run Optimization
4. Explore the **Map View**, **Simulator**, and **AI Recommendations**

---

## 🏗️ Architecture

```
optiload-ai/
├── backend/
│   ├── auth-service/          Port 8001 — JWT Authentication
│   ├── ingestion-service/     Port 8002 — CSV upload & validation
│   ├── clustering-service/    Port 8003 — DBSCAN+KMeans+Graph clustering
│   ├── optimization-service/  Port 8004 — OR-Tools VRP + PuLP MILP
│   ├── simulation-service/    Port 8005 — Monte Carlo simulation
│   └── analytics-service/    Port 8006 — Dashboard metrics & KPIs
├── frontend/
│   └── dashboard/            Port 3000 — React + TypeScript + Tailwind
├── ai/
│   ├── clustering/            Embedding & graph models
│   ├── routing/               VRP + MILP + carbon calculation
│   └── reinforcement_learning/ Deep Q-Network logistics optimizer
├── data/
│   └── demo_dataset/          200 shipments + 20 vehicles (Indian cities)
├── infra/
│   └── docker/               Prometheus + Grafana config
└── tests/                    Unit + Integration tests
```

### Technology Stack

| Layer | Technologies |
|-------|-------------|
| **Backend** | Python, FastAPI, Celery, Pydantic |
| **AI/Optimization** | OR-Tools, PuLP, PyTorch (DQN), NetworkX, scikit-learn |
| **Database** | PostgreSQL + PostGIS, Redis |
| **Queue** | RabbitMQ |
| **Frontend** | React 18, TypeScript, Tailwind CSS, Recharts, Mapbox GL JS |
| **Observability** | Prometheus, Grafana, OpenTelemetry |
| **Deployment** | Docker, docker-compose |

---

## 🔌 API Endpoints

### Auth Service (`:8001`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register new user |
| POST | `/auth/login` | Login (returns JWT) |
| POST | `/auth/refresh` | Refresh token |
| GET | `/auth/me` | Current user profile |

### Ingestion Service (`:8002`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/shipments/upload` | Upload CSV file |
| POST | `/api/shipments/single` | Create single shipment |
| GET | `/api/shipments` | List all shipments |
| POST | `/api/vehicles/bulk` | Upload vehicles CSV |
| POST | `/api/demo/load` | Load demo dataset |

### Clustering Service (`:8003`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/clusters/run` | Run hybrid clustering |
| GET | `/api/clusters` | List clusters |
| POST | `/api/clusters/compatibility-check` | Check two shipments |

### Optimization Service (`:8004`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/optimize?algorithm=vrp\|milp\|ffd` | Run optimization |
| GET | `/api/routes` | List optimized routes |
| GET | `/api/carbon/report` | Carbon emission report |

### Simulation Service (`:8005`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/simulate` | Run Monte Carlo |
| GET | `/api/simulate/history` | Past sim results |

### Analytics Service (`:8006`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/metrics` | Full dashboard metrics |
| GET | `/api/metrics/kpi` | Lightweight KPI summary |
| GET | `/api/recommendations` | AI recommendations |
| GET | `/api/metrics/history` | Historical trend data |

---

## 🤖 AI Optimization Algorithms

### 1. Shipment Clustering
- **Haversine distance** for geospatial proximity
- **Cosine similarity** on `[origin_lat, origin_lng, dest_lat, dest_lng]` route vectors
- **Time window overlap** for temporal compatibility
- **NetworkX graph** + Louvain community detection
- **DBSCAN** (eps=50km) + **KMeans** hybrid

### 2. Vehicle Routing (VRP)
- Google **OR-Tools** `pywrapcp` solver
- Handles: capacity constraints, time windows, pickup-delivery pairs
- Nearest-neighbor TSP fallback for fast approximation

### 3. MILP Optimization (PuLP)
- Decision variable: `x[i][j]` = shipment `i` assigned to vehicle `j`
- Objective: `min α·distance + β·empty_cap + γ·trips + δ·CO₂`
- CBC solver with 4-second time limit

### 4. Load Consolidation
- **First Fit Decreasing (FFD)** bin packing
- Best-fit variant: assigns to vehicle with minimum sufficient remaining capacity

### 5. Monte Carlo Simulation
- 50–1000 simulation runs
- Random variables: fleet size, shipment volume, traffic delay, fuel cost
- Outputs: P5/P95 cost bounds, utilization distribution, CO₂ savings

### 6. Reinforcement Learning
- **Deep Q-Network** (DQN) with PyTorch
- State: cluster features + fleet availability
- Actions: merge clusters, split cluster, assign vehicle, delay shipment
- Reward: +utilization −cost −emissions −trips
- Train manually: `docker exec -it optiload-rl python train.py`

---

## 🗺️ Map View

The map uses **Mapbox GL JS** for interactive visualization. To enable:

1. Get a free token at [mapbox.com](https://mapbox.com)
2. Set it in `frontend/dashboard/.env`:
   ```
   VITE_MAPBOX_TOKEN=pk.your_token_here
   ```
3. Rebuild: `docker-compose up --build frontend`

Without a token, the map shows a static dot visualization.

---

## 🧪 Testing

```bash
# Unit tests (no services needed)
pip install -r tests/requirements.txt
pytest tests/unit/ -v

# Integration tests (services must be running)
pytest tests/integration/ -v

# All tests
pytest tests/ -v
```

---

## 📊 Demo Dataset

The synthetic dataset covers 20 major Indian cities:

**Mumbai, Delhi, Bangalore, Chennai, Hyderabad, Pune, Ahmedabad, Kolkata, Jaipur, Surat, Lucknow, Nagpur, Indore, Bhopal, Visakhapatnam, Coimbatore, Kochi, Chandigarh, Guwahati, Bhubaneswar**

- **200 shipments** with realistic weights (100-12,000 kg) and volumes
- **20 vehicles** across 5 types (mini, medium, large, heavy, refrigerated)
- Cargo types: electronics, textiles, pharmaceuticals, automotive, food, furniture, chemicals

Regenerate:
```bash
cd data/demo_dataset && python3 generate.py
```

---

## 🔧 Environment Variables

Each service reads from environment variables (set in `docker-compose.yml`):

| Variable | Default | Used by |
|----------|---------|---------|
| `DATABASE_URL` | `postgresql://optiload:...` | All backend |
| `REDIS_URL` | `redis://redis:6379/N` | All backend |
| `RABBITMQ_URL` | `amqp://optiload:...` | Clustering, Optimization |
| `JWT_SECRET` | `super-secret...` | Auth |
| `VITE_MAPBOX_TOKEN` | (empty) | Frontend |

---

## ☁️ Cloud Deployment

### AWS
```bash
# ECS / Fargate:
aws ecr create-repository --repository-name optiload-ai
docker-compose push
# Deploy via ECS Task Definitions or AWS Copilot
```

### GCP
```bash
gcloud run deploy optiload-auth --source ./backend/auth-service
# Repeat for each service
```

### Azure
```bash
az containerapp create --name optiload-auth --image optiload-auth:latest
```

For production, replace PostgreSQL with **AWS RDS**, Redis with **ElastiCache**, and RabbitMQ with **Amazon MQ**.

---

## 🛡️ Security

- JWT access tokens (60 min) + refresh tokens (7 days)
- Redis token blacklist for logout
- Pydantic v2 input validation on all endpoints
- CORS configured (restrict `allow_origins` in production)
- bcrypt password hashing

---

## 📈 Performance

- Shipments: **500+/day** supported
- Fleet: **50 vehicles**
- Optimization time: **< 5 seconds** (FFD ≈ 100ms, VRP ≈ 4s, MILP ≈ 4s)
- Redis caching: Metrics cached 30s, optimization results 120s

---

*Built with ❤️ for production-grade AI logistics optimization.*
