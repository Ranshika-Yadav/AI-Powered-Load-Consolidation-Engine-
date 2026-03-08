-- OptiLoad AI Database Initialization
-- Enable PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    role VARCHAR(50) DEFAULT 'operator',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Shipments table
CREATE TABLE IF NOT EXISTS shipments (
    shipment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    origin_lat FLOAT NOT NULL,
    origin_lng FLOAT NOT NULL,
    destination_lat FLOAT NOT NULL,
    destination_lng FLOAT NOT NULL,
    origin_city VARCHAR(100),
    destination_city VARCHAR(100),
    weight FLOAT NOT NULL,
    volume FLOAT NOT NULL,
    pickup_time TIMESTAMP NOT NULL,
    delivery_deadline TIMESTAMP NOT NULL,
    priority INT DEFAULT 1,
    status TEXT DEFAULT 'pending',
    cargo_type VARCHAR(100) DEFAULT 'general',
    special_requirements TEXT,
    cluster_id UUID,
    created_at TIMESTAMP DEFAULT NOW(),
    origin_location GEOGRAPHY(POINT, 4326),
    destination_location GEOGRAPHY(POINT, 4326)
);

-- Vehicles table
CREATE TABLE IF NOT EXISTS vehicles (
    vehicle_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vehicle_type VARCHAR(100) NOT NULL,
    registration_number VARCHAR(50),
    capacity_weight FLOAT NOT NULL,
    capacity_volume FLOAT NOT NULL,
    cost_per_km FLOAT NOT NULL,
    fuel_efficiency FLOAT NOT NULL,
    co2_per_km FLOAT NOT NULL,
    availability_status BOOLEAN DEFAULT TRUE,
    current_location GEOGRAPHY(POINT, 4326),
    current_lat FLOAT,
    current_lng FLOAT,
    current_city VARCHAR(100),
    driver_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Clusters table
CREATE TABLE IF NOT EXISTS clusters (
    cluster_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    shipment_ids UUID[] NOT NULL,
    cluster_weight FLOAT,
    cluster_volume FLOAT,
    centroid_lat FLOAT,
    centroid_lng FLOAT,
    compatibility_score FLOAT,
    algorithm VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Routes table
CREATE TABLE IF NOT EXISTS routes (
    route_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vehicle_id UUID REFERENCES vehicles(vehicle_id),
    cluster_id UUID REFERENCES clusters(cluster_id),
    shipment_ids UUID[],
    stop_sequence JSONB,
    total_distance FLOAT,
    total_cost FLOAT,
    utilization_percent FLOAT,
    estimated_co2 FLOAT,
    fuel_consumption FLOAT,
    estimated_duration INTERVAL,
    status TEXT DEFAULT 'planned',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Simulation Results table
CREATE TABLE IF NOT EXISTS simulation_results (
    sim_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    simulation_name VARCHAR(200),
    num_simulations INT,
    fleet_size INT,
    shipment_volume INT,
    avg_utilization FLOAT,
    total_cost FLOAT,
    fuel_usage FLOAT,
    co2_emission FLOAT,
    trip_count FLOAT,
    cost_savings FLOAT,
    co2_savings FLOAT,
    percentile_5_cost FLOAT,
    percentile_95_cost FLOAT,
    raw_results JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Optimization Jobs table
CREATE TABLE IF NOT EXISTS optimization_jobs (
    job_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    status TEXT DEFAULT 'pending',
    algorithm VARCHAR(50),
    num_shipments INT,
    num_vehicles INT,
    result JSONB,
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Metrics Snapshots table
CREATE TABLE IF NOT EXISTS metrics_snapshots (
    snapshot_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    total_shipments INT,
    pending_shipments INT,
    optimized_shipments INT,
    total_vehicles INT,
    active_vehicles INT,
    avg_utilization FLOAT,
    total_cost FLOAT,
    total_co2 FLOAT,
    trips_saved INT,
    cost_savings FLOAT,
    co2_savings FLOAT,
    snapshot_at TIMESTAMP DEFAULT NOW()
);

-- Insert demo admin user (password: demo123)
INSERT INTO users (username, email, hashed_password, role)
VALUES (
    'admin',
    'admin@optiload.ai',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMeSSTPqGbNbVD9Q.dSFj.V0Vy',
    'admin'
) ON CONFLICT (username) DO NOTHING;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_shipments_status ON shipments(status);
CREATE INDEX IF NOT EXISTS idx_shipments_cluster ON shipments(cluster_id);
CREATE INDEX IF NOT EXISTS idx_routes_vehicle ON routes(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_routes_created ON routes(created_at);
