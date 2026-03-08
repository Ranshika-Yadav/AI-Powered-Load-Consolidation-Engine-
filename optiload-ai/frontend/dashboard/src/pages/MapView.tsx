import { useEffect, useRef, useState } from 'react';
import { useQuery } from 'react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { Map as MapIcon, Layers, Package, Truck, AlertCircle } from 'lucide-react';
import { getShipments, getVehicles, getRoutes } from '../api/client';

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN || '';
const INDIA_CENTER: [number, number] = [78.9629, 20.5937];

const pageVariants = {
  hidden: { opacity: 0, y: 15 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: 'easeOut' } }
};

function MapFallback({ shipments, vehicles, routes }: any) {
  return (
    <div className="relative w-full h-full bg-[#0a0f1e] rounded-xl overflow-hidden flex flex-col items-center justify-center border border-white/5">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-indigo-500/10 via-transparent to-transparent opacity-50" />
      
      <div className="text-center z-10 p-8 max-w-lg">
        <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mx-auto mb-5 shadow-[0_0_30px_rgba(99,102,241,0.15)]">
          <MapIcon className="w-8 h-8 text-indigo-400" />
        </div>
        <h3 className="text-xl text-white font-bold tracking-tight mb-2">Interactive Map Locked</h3>
        <p className="text-slate-400 text-sm leading-relaxed mb-6">
          Add your Mapbox API token to <code className="text-indigo-300 text-[11px] bg-indigo-900/30 px-1.5 py-0.5 rounded border border-indigo-500/20 font-mono">VITE_MAPBOX_TOKEN</code> in your environment file to unlock the live interactive geospatial visualization.
        </p>
        
        {/* Data summary */}
        <div className="grid grid-cols-3 gap-3 w-full">
          <div className="glass-card p-4 text-center hover:border-indigo-500/30 transition-colors">
            <div className="text-2xl font-black text-indigo-400">{(shipments || []).length}</div>
            <div className="text-[11px] text-slate-500 font-semibold uppercase tracking-wider mt-1">Shipments</div>
          </div>
          <div className="glass-card p-4 text-center hover:border-emerald-500/30 transition-colors">
            <div className="text-2xl font-black text-emerald-400">{(vehicles || []).length}</div>
            <div className="text-[11px] text-slate-500 font-semibold uppercase tracking-wider mt-1">Vehicles</div>
          </div>
          <div className="glass-card p-4 text-center hover:border-amber-500/30 transition-colors">
            <div className="text-2xl font-black text-amber-400">{(routes || []).length}</div>
            <div className="text-[11px] text-slate-500 font-semibold uppercase tracking-wider mt-1">Routes</div>
          </div>
        </div>
      </div>

      {/* Decorative dots */}
      {(shipments || []).slice(0, 40).map((s: any, i: number) => {
        const x = 20 + (((s.origin_lng || 78) - 65) / 30) * 60;
        const y = 10 + ((30 - (s.origin_lat || 20)) / 25) * 80;
        return (
          <motion.div 
            initial={{ opacity: 0, scale: 0 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: i * 0.02 }}
            key={i} 
            className="absolute w-1.5 h-1.5 rounded-full bg-indigo-500/40 shadow-[0_0_8px_rgba(99,102,241,0.5)]"
            style={{ left: `${Math.max(5, Math.min(95, x))}%`, top: `${Math.max(5, Math.min(95, y))}%` }}
          />
        );
      })}
    </div>
  );
}

function MapboxView({ shipments, vehicles, routes }: any) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);

  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return;
    
    const loadMap = async () => {
      try {
        const mapboxgl = (await import('mapbox-gl')).default;
        mapboxgl.accessToken = MAPBOX_TOKEN;

        const map = new mapboxgl.Map({
          container: mapContainer.current!,
          style: 'mapbox://styles/mapbox/dark-v11',
          center: INDIA_CENTER,
          zoom: 4.5,
          pitch: 20,
        });
        mapRef.current = map;

        map.addControl(new mapboxgl.NavigationControl(), 'top-right');

        map.on('load', () => {
          (shipments || []).slice(0, 200).forEach((s: any) => {
            const el = document.createElement('div');
            el.className = 'w-3 h-3 rounded-full border-2 cursor-pointer shadow-[0_0_10px_rgba(99,102,241,0.6)]';
            el.style.background = '#6366f1';
            el.style.borderColor = '#818cf8';

            new mapboxgl.Marker(el)
              .setLngLat([s.origin_lng, s.origin_lat])
              .setPopup(new mapboxgl.Popup({ offset: 10, className: 'mapbox-popup-dark' })
                .setHTML(`<div style="background:#0f172a;padding:12px;border-radius:12px;color:#f8fafc;font-size:12px;border:1px solid rgba(255,255,255,0.1)">
                  <strong>${s.origin_city || 'Shipment'} → ${s.destination_city || ''}</strong><br/>
                  Weight: ${s.weight} kg | Volume: ${s.volume} m³<br/>
                  Priority: ${s.priority} | Status: ${s.status}
                </div>`))
              .addTo(map);

            const el2 = document.createElement('div');
            el2.className = 'w-2 h-2 rounded-full border border-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]';
            el2.style.background = '#10b981';

            new mapboxgl.Marker(el2)
              .setLngLat([s.destination_lng, s.destination_lat]).addTo(map);

            const routeId = `route-${s.shipment_id}`;
            if (!map.getSource(routeId)) {
              map.addSource(routeId, {
                type: 'geojson',
                data: {
                  type: 'Feature',
                  geometry: {
                    type: 'LineString',
                    coordinates: [[s.origin_lng, s.origin_lat], [s.destination_lng, s.destination_lat]],
                  },
                  properties: {},
                }
              });
              map.addLayer({
                id: routeId,
                type: 'line',
                source: routeId,
                paint: {
                  'line-color': s.status === 'optimized' ? '#10b981' : '#6366f1',
                  'line-width': 1.5,
                  'line-opacity': 0.4,
                  'line-dasharray': [2, 2],
                },
              });
            }
          });

          (vehicles || []).forEach((v: any) => {
            if (!v.current_lat || !v.current_lng) return;
            const el = document.createElement('div');
            el.className = 'w-3.5 h-3.5 rounded-sm border-2 border-amber-400 shadow-[0_0_10px_rgba(245,158,11,0.5)] cursor-pointer';
            el.style.background = '#f59e0b';
            new mapboxgl.Marker(el)
              .setLngLat([v.current_lng, v.current_lat])
              .setPopup(new mapboxgl.Popup({ offset: 10 })
                .setHTML(`<div style="background:#0f172a;padding:12px;border-radius:12px;color:#f8fafc;font-size:12px;border:1px solid rgba(255,255,255,0.1)">
                  <strong>🚛 ${v.vehicle_type} | ${v.current_city}</strong><br/>
                  Cap: ${v.capacity_weight}kg / ${v.capacity_volume}m³
                </div>`))
              .addTo(map);
          });
        });
      } catch (e) {
        console.error('Mapbox failed to load:', e);
      }
    };
    loadMap();

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, [shipments, vehicles]);

  return <div ref={mapContainer} className="w-full h-full rounded-2xl" />;
}

export default function MapPage() {
  const [activeLayer, setActiveLayer] = useState<'shipments' | 'vehicles' | 'routes'>('shipments');
  
  const { data: shipments } = useQuery('shipments-map', () => getShipments(200).then(r => r.data), { onError: () => {} });
  const { data: vehicles } = useQuery('vehicles-map', () => getVehicles().then(r => r.data), { onError: () => {} });
  const { data: routes } = useQuery('routes-map', () => getRoutes().then(r => r.data), { onError: () => {} });

  const hasToken = MAPBOX_TOKEN && MAPBOX_TOKEN !== 'pk.demo_token_replace_with_real' && MAPBOX_TOKEN.startsWith('pk.');

  return (
    <motion.div variants={pageVariants} initial="hidden" animate="visible" className="p-8 min-h-full flex flex-col max-w-[1600px] mx-auto">
      
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between mb-8 gap-4">
        <div>
          <h1 className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-white to-slate-400 tracking-tight">Geospatial Overview</h1>
          <p className="text-slate-400 text-sm mt-1.5 font-medium">Live tracking of logistics assets and optimized paths</p>
        </div>

        <div className="flex gap-2">
          {([
            { id: 'shipments', icon: Package, label: 'Shipments', count: (shipments || []).length },
            { id: 'vehicles', icon: Truck, label: 'Vehicles', count: (vehicles || []).length },
            { id: 'routes', icon: Layers, label: 'Routes', count: (routes || []).length },
          ] as const).map(({ id, icon: Icon, label, count }) => (
            <motion.button 
              whileTap={{ scale: 0.95 }}
              key={id} id={`layer-${id}`}
              onClick={() => setActiveLayer(id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all shadow-sm ${
                activeLayer === id
                  ? 'bg-indigo-500 text-white shadow-[0_4px_12px_rgba(99,102,241,0.3)]'
                  : 'bg-[#1e293b] border border-white/5 text-slate-400 hover:text-white hover:bg-[#334155]'
              }`}>
              <Icon className="w-3.5 h-3.5" />
              {label} ({count})
            </motion.button>
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className="flex gap-5 mb-5 text-[11px] font-semibold uppercase tracking-wider">
        {[
          { color: '#6366f1', label: 'Origin Node' },
          { color: '#10b981', label: 'Target Destination' },
          { color: '#f59e0b', label: 'Active Fleet' },
          { color: '#10b981', label: 'Optimized Path' },
        ].map(({ color, label }) => (
          <div key={label} className="flex items-center gap-2 text-slate-400">
            <div className="w-2.5 h-2.5 rounded-full" style={{ background: color, boxShadow: `0 0 8px ${color}80` }} />
            {label}
          </div>
        ))}
      </div>

      {/* Map Container */}
      <div className="flex-1 min-h-[600px] glass-card p-1">
        {hasToken
          ? <MapboxView shipments={shipments} vehicles={vehicles} routes={routes} />
          : <MapFallback shipments={shipments} vehicles={vehicles} routes={routes} />}
      </div>
    </motion.div>
  );
}
