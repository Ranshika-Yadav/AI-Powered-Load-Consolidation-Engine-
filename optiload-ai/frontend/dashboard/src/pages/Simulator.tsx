import { useState } from 'react';
import { motion } from 'framer-motion';
import { useMutation } from 'react-query';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, CartesianGrid } from 'recharts';
import { FlaskConical, Play, Loader2, BarChart3, CloudRain, Coins } from 'lucide-react';
import { runSimulation } from '../api/client';
import toast from 'react-hot-toast';

interface SimParams {
  num_simulations: number;
  base_fleet_size: number;
  base_shipment_volume: number;
  avg_distance_km: number;
  fuel_cost_base: number;
  simulation_name: string;
  fleet_size_std: number;
  shipment_volume_std: number;
  traffic_delay_mean: number;
}

function Slider({ label, value, min, max, step, onChange, unit, id, colorClass = "from-indigo-500 to-indigo-400" }: any) {
  const percent = ((value - min) / (max - min)) * 100;
  
  return (
    <div className="mb-5 last:mb-0">
      <div className="flex justify-between items-center mb-2.5">
        <span className="text-[13px] font-semibold text-slate-300">{label}</span>
        <div className="bg-[#0f172a] px-2.5 py-1 rounded-md border border-white/5 text-[11px] font-bold text-indigo-300">
          {value}{unit}
        </div>
      </div>
      <div className="relative h-2 rounded-full bg-slate-800">
        <div 
          className={`absolute left-0 top-0 h-full rounded-full bg-gradient-to-r ${colorClass}`}
          style={{ width: `${percent}%` }}
        />
        <input 
          id={id} type="range" min={min} max={max} step={step} value={value}
          onChange={e => onChange(+e.target.value)}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        />
      </div>
      <div className="flex justify-between text-[10px] font-medium text-slate-500 mt-2 px-1">
        <span>{min}{unit}</span>
        <span>{max}{unit}</span>
      </div>
    </div>
  );
}

const pageVariants = {
  hidden: { opacity: 0, scale: 0.98 },
  visible: { opacity: 1, scale: 1, transition: { duration: 0.4, ease: [0.22, 1, 0.36, 1] } }
};

export default function SimulatorPage() {
  const [params, setParams] = useState<SimParams>({
    num_simulations: 300,
    base_fleet_size: 20,
    base_shipment_volume: 200,
    avg_distance_km: 350,
    fuel_cost_base: 92,
    simulation_name: 'Q3 Stress Test',
    fleet_size_std: 3,
    shipment_volume_std: 20,
    traffic_delay_mean: 1.2,
  });

  const [result, setResult] = useState<any>(null);

  const mutation = useMutation('runSimulation', (p: SimParams) => runSimulation(p as any).then(r => r.data), {
    onSuccess: (data) => {
      setResult(data);
      toast.success(`Simulation complete! Generated ${data.num_simulations} futures.`);
    },
    onError: () => { toast.error('Simulation engine failed to connect.'); },
  });

  const update = (key: keyof SimParams) => (v: number) => setParams(p => ({ ...p, [key]: v }));

  const histData = result?.histogram_costs
    ? (() => {
        const costs: number[] = result.histogram_costs;
        const [min, max] = [Math.min(...costs), Math.max(...costs)];
        const bins = 20;
        const binSize = (max - min) / bins || 1;
        const freq: Record<number, number> = {};
        costs.forEach(c => {
          const bin = Math.floor((c - min) / binSize);
          const label = Math.round(min + bin * binSize);
          freq[label] = (freq[label] || 0) + 1;
        });
        return Object.entries(freq).map(([k, v]) => ({ cost: +k, count: v })).sort((a, b) => a.cost - b.cost);
      })()
    : [];

  return (
    <motion.div variants={pageVariants} initial="hidden" animate="visible" className="p-8 min-h-full max-w-7xl mx-auto">
      
      {/* Header */}
      <div className="flex items-center gap-4 mb-10">
        <div className="w-12 h-12 rounded-2xl bg-fuchsia-500/10 border border-fuchsia-500/20 flex items-center justify-center shadow-[0_0_20px_rgba(217,70,239,0.15)]">
          <FlaskConical className="w-6 h-6 text-fuchsia-400" />
        </div>
        <div>
          <h1 className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-white to-slate-400 tracking-tight">Monte Carlo Engine</h1>
          <p className="text-slate-400 text-sm mt-1.5 font-medium">Stochastic operations modeling and risk analysis</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Input Matrix */}
        <div className="lg:col-span-4 glass-card p-6 flex flex-col h-[calc(100vh-12rem)] min-h-[700px]">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-6 pb-4 border-b border-white/5">Scenario Variables</h3>
          
          <div className="flex-1 overflow-y-auto pr-2 no-scrollbar">
            <div className="mb-6">
              <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-2">Scenario Ident</label>
              <input id="sim-name" type="text" value={params.simulation_name}
                onChange={e => setParams(p => ({ ...p, simulation_name: e.target.value }))}
                className="w-full bg-[#0a0f1e] text-white text-sm font-mono px-4 py-3 rounded-xl border border-white/5 focus:border-fuchsia-500/50 outline-none transition-colors" />
            </div>

            <div className="space-y-1">
              <Slider id="fleet-size" label="Baseline Fleet Count" value={params.base_fleet_size} min={5} max={50} step={1}
                onChange={update('base_fleet_size')} unit="" colorClass="from-fuchsia-600 to-fuchsia-400" />
              <div className="h-px bg-white/5 my-4" />
              
              <Slider id="shipment-volume" label="Expected Output Volume" value={params.base_shipment_volume} min={50} max={500} step={10}
                onChange={update('base_shipment_volume')} unit="" colorClass="from-emerald-600 to-emerald-400" />
              <div className="h-px bg-white/5 my-4" />
              
              <Slider id="avg-distance" label="Mean Path Length" value={params.avg_distance_km} min={100} max={1000} step={50}
                onChange={update('avg_distance_km')} unit="km" colorClass="from-amber-600 to-amber-400" />
              <div className="h-px bg-white/5 my-4" />
              
              <Slider id="fuel-cost" label="Petroleum Spot Price" value={params.fuel_cost_base} min={70} max={130} step={1}
                onChange={update('fuel_cost_base')} unit="₹" />
              <div className="h-px bg-white/5 my-4" />
              
              <Slider id="traffic-delay" label="Stochastic Delay Modifier" value={params.traffic_delay_mean} min={1.0} max={2.0} step={0.05}
                onChange={update('traffic_delay_mean')} unit="x" />
              <div className="h-px bg-white/5 my-4" />
              
              <Slider id="num-sims" label="Monte Carlo Iterations" value={params.num_simulations} min={50} max={1000} step={50}
                onChange={update('num_simulations')} unit="" colorClass="from-slate-600 to-slate-400" />
            </div>
          </div>

          <div className="pt-6 mt-auto border-t border-white/5">
            <motion.button 
              whileTap={{ scale: 0.98 }}
              onClick={() => mutation.mutate(params)} disabled={mutation.isLoading}
              className="w-full py-4 rounded-xl bg-fuchsia-600 hover:bg-fuchsia-500 text-white font-bold flex items-center justify-center gap-2 transition-colors shadow-[0_0_20px_rgba(192,38,211,0.3)] hover:shadow-[0_0_30px_rgba(192,38,211,0.5)]"
            >
              {mutation.isLoading
                ? <><Loader2 className="w-5 h-5 animate-spin" /> Computing Models...</>
                : <><Play className="w-5 h-5" /> Execute Simulation</>}
            </motion.button>
          </div>
        </div>

        {/* Results Matrix */}
        <div className="lg:col-span-8 flex flex-col gap-6">
          {!result && !mutation.isLoading && (
            <div className="glass-card flex-1 flex flex-col items-center justify-center text-center p-12 relative overflow-hidden">
              <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-fuchsia-900/20 via-[#0a0f1e] to-[#0a0f1e]" />
              <div className="w-24 h-24 rounded-full bg-slate-800/50 flex items-center justify-center mb-6 border border-white/5 shadow-inner z-10">
                <FlaskConical className="w-10 h-10 text-slate-500" />
              </div>
              <h3 className="text-xl font-bold text-white z-10 tracking-tight">System Ready for Scenario</h3>
              <p className="text-slate-400 text-sm mt-3 max-w-sm z-10 leading-relaxed font-medium">
                Design your hypotheticals on the left matrix and execute the engine to forecast operational resilience and cost ceilings.
              </p>
            </div>
          )}

          {mutation.isLoading && (
            <div className="glass-card flex-1 flex flex-col items-center justify-center text-center p-12">
              <Loader2 className="w-16 h-16 text-fuchsia-500 animate-spin mb-6 drop-shadow-[0_0_15px_rgba(217,70,239,0.5)]" />
              <h3 className="text-2xl font-bold text-white tracking-tight">Generating {params.num_simulations} Realities</h3>
              <p className="text-fuchsia-300 text-sm mt-2 font-mono flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-fuchsia-500 animate-pulse" /> Running stochastic distribution
              </p>
            </div>
          )}

          {result && !mutation.isLoading && (
            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="flex flex-col gap-6 h-full">
              
              {/* Top Output Layer */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {[
                  { label: 'Mean Asset Utilization', value: `${result.avg_utilization}%`, icon: BarChart3, color: 'text-indigo-400', bg: 'bg-indigo-500/10' },
                  { label: 'Projected Opex Relief', value: `₹${(result.cost_savings / 1000).toFixed(0)}K`, icon: Coins, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
                  { label: 'Est. Total Emission Drop', value: `${(result.co2_savings / 1000).toFixed(1)}T`, icon: CloudRain, color: 'text-sky-400', bg: 'bg-sky-500/10' },
                ].map(({ label, value, icon: Icon, color, bg }, i) => (
                  <motion.div 
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.1 }}
                    key={label} className="glass-card p-6 flex flex-col items-start"
                  >
                    <div className={`w-10 h-10 rounded-xl ${bg} flex items-center justify-center mb-4`}>
                      <Icon className={`w-5 h-5 ${color}`} />
                    </div>
                    <div className="text-3xl font-black text-white tracking-tight mb-1">{value}</div>
                    <div className="text-xs text-slate-400 font-bold uppercase tracking-wider">{label}</div>
                  </motion.div>
                ))}
              </div>

              {/* Data Visualization Layer */}
              <div className="glass-card p-6 flex-1 flex flex-col">
                <h3 className="section-title">Cost Probability Distribution (N={result.num_simulations})</h3>
                <div className="flex-1 mt-4 min-h-[250px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={histData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <CartesianGrid vertical={false} stroke="rgba(255,255,255,0.02)" />
                      <XAxis dataKey="cost" tick={{ fill: '#64748b', fontSize: 11 }}
                        axisLine={false} tickLine={false} tickFormatter={v => `₹${(v/1000).toFixed(0)}K`} dy={10} />
                      <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                      <Tooltip formatter={(v: any) => [v, 'Occurrences']}
                        labelFormatter={(l) => `Est. Total: ₹${l.toLocaleString()}`} cursor={{ fill: 'rgba(255,255,255,0.02)' }} />
                      <ReferenceLine x={result.total_cost} stroke="#d946ef" strokeDasharray="4 4" strokeWidth={2} label={{ value: 'Mean Expectation', fill: '#d946ef', fontSize: 11, position: 'top' }} />
                      <Bar dataKey="count" fill="url(#histGrad)" radius={[4, 4, 0, 0]} animationDuration={1000} />
                      <defs>
                        <linearGradient id="histGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#d946ef" />
                          <stop offset="100%" stopColor="#86198f" />
                        </linearGradient>
                      </defs>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                
                {/* Statistics Footer */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 pt-6 border-t border-white/5">
                  {[
                    { l: 'Mean Cost', v: `₹${(result.total_cost / 1000).toFixed(0)}K` },
                    { l: 'Base Operations', v: `₹${(result.baseline_cost / 1000).toFixed(0)}K` },
                    { l: 'P95 Extreme', v: `₹${(result.percentile_95_cost / 1000).toFixed(0)}K`, warn: true },
                    { l: 'Fuel Usage (L)', v: result.fuel_usage.toFixed(0) },
                  ].map(stat => (
                    <div key={stat.l} className="bg-slate-900/50 p-3 rounded-xl border border-white/5 text-center">
                      <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-1">{stat.l}</div>
                      <div className={`text-sm font-mono font-bold ${stat.warn ? 'text-rose-400' : 'text-slate-200'}`}>{stat.v}</div>
                    </div>
                  ))}
                </div>
              </div>

            </motion.div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
