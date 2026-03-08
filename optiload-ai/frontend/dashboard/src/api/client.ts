import axios from 'axios';

const AUTH_URL = import.meta.env.VITE_AUTH_URL || 'http://localhost:8001';
const INGESTION_URL = import.meta.env.VITE_INGESTION_URL || 'http://localhost:8002';
const CLUSTERING_URL = import.meta.env.VITE_CLUSTERING_URL || 'http://localhost:8003';
const OPTIMIZATION_URL = import.meta.env.VITE_OPTIMIZATION_URL || 'http://localhost:8004';
const SIMULATION_URL = import.meta.env.VITE_SIMULATION_URL || 'http://localhost:8005';
const ANALYTICS_URL = import.meta.env.VITE_ANALYTICS_URL || 'http://localhost:8006';

const makeClient = (baseURL: string) => {
  const client = axios.create({ baseURL, timeout: 30000 });
  client.interceptors.request.use(config => {
    const token = localStorage.getItem('access_token');
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
  });
  return client;
};

export const authApi = makeClient(AUTH_URL);
export const ingestionApi = makeClient(INGESTION_URL);
export const clusteringApi = makeClient(CLUSTERING_URL);
export const optimizationApi = makeClient(OPTIMIZATION_URL);
export const simulationApi = makeClient(SIMULATION_URL);
export const analyticsApi = makeClient(ANALYTICS_URL);

// Auth helpers
export const login = (username: string, password: string) => {
  const form = new FormData();
  form.append('username', username);
  form.append('password', password);
  return authApi.post('/auth/login', form);
};

export const getMe = () => authApi.get('/auth/me');

// Analytics
export const getDashboardMetrics = () => analyticsApi.get('/api/metrics');
export const getKpi = () => analyticsApi.get('/api/metrics/kpi');
export const getRecommendations = () => analyticsApi.get('/api/recommendations');
export const getMetricsHistory = (days = 7) => analyticsApi.get(`/api/metrics/history?days=${days}`);

// Shipments
export const getShipments = (limit = 100) => ingestionApi.get(`/api/shipments?limit=${limit}`);
export const uploadShipments = (file: File) => {
  const form = new FormData();
  form.append('file', file);
  return ingestionApi.post('/api/shipments/upload', form);
};
export const loadDemoData = () => ingestionApi.post('/api/demo/load');

// Vehicles
export const getVehicles = () => ingestionApi.get('/api/vehicles');

// Clustering
export const runClustering = () => clusteringApi.post('/api/clusters/run');
export const getClusters = () => clusteringApi.get('/api/clusters');

// Optimization
export const runOptimization = (algorithm = 'vrp') =>
  optimizationApi.post(`/api/optimize?algorithm=${algorithm}`);
export const getRoutes = () => optimizationApi.get('/api/routes');
export const getCarbonReport = () => optimizationApi.get('/api/carbon/report');

// Simulation
export const runSimulation = (params: Record<string, unknown>) =>
  simulationApi.post('/api/simulate', params);
export const getSimulationHistory = () => simulationApi.get('/api/simulate/history');
