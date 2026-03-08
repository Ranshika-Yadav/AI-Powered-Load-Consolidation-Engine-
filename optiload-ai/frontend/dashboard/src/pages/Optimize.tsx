import { useQuery, useMutation, useQueryClient } from 'react-query';
import { motion } from 'framer-motion';
import { Zap, Loader2, RefreshCw, Network } from 'lucide-react';
import { runOptimization, runClustering, getRoutes, getCarbonReport } from '../api/client';
import toast from 'react-hot-toast';
import { useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, CartesianGrid } from 'recharts';

const pageVariants = {
  hidden: { opacity: 0, y: 15 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4, staggerChildren: 0.1 } }
};

const itemVariants = {
  hidden: { opacity: 0, y: 10 },
  visible: { opacity: 1, y: 0 }
};

export default function OptimizePage() {
  const queryClient = useQueryClient();
  const [algorithm, setAlgorithm] = useState<'vrp' | 'milp' | 'ffd'>('vrp');

  const { data: routes } = useQuery('routes', () => getRoutes().then(r => r.data));
  const { data: carbon } = useQuery('carbon', () => getCarbonReport().then(r => r.data));

  const clusterMutation = useMutation('runClustering', () => runClustering().then(r => r.data), {
    onSuccess: (data) => {
      toast.success(`Created ${data.num_clusters} semantic clusters`);
      queryClient.invalidateQueries('routes');
    },
    onError: () => { toast.error('Clustering engine failed'); },
  });

  const optimizeMutation = useMutation('runOptimization', () => runOptimization(algorithm).then(r => r.data), {
    onSuccess: (data) => {
      toast.success(`Optimization complete! ${data.num_routes} paths generated.`);
      queryClient.invalidateQueries('routes');
      queryClient.invalidateQueries('dashboard-metrics');
      queryClient.invalidateQueries('carbon');
    },
    onError: () => { toast.error('Solver engine failed'); },
  });

  const algos = [
    { id: 'vrp', label: 'OR-Tools VRP Solver', desc: 'Google Operations Research — Highest efficiency', icon: '⚡' },
    { id: 'milp', label: 'PuLP MILP', desc: 'Multi-objective linear programming', icon: '📐' },
    { id: 'ffd', label: 'FFD Heuristic', desc: 'First Fit Decreasing — Fastest execution', icon: '🚀' },
  ];

  const routeData = (routes || []).slice(0, 15).map((r: any, i: number) => ({
    name: `V${i + 1}`,
    utilization: r.utilization_percent,
    cost: r.total_cost,
    co2: r.estimated_co2,
  }));

  return (
    <motion.div variants={pageVariants} initial="hidden" animate="visible" className="p-8 min-h-full max-w-7xl mx-auto">
      
      {/* Header */}
      <div className="flex items-center gap-4 mb-10">
        <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center shadow-[0_0_20px_rgba(99,102,241,0.15)]">
          <Zap className="w-6 h-6 text-indigo-400" />
        </div>
        <div>
          <h1 className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-white to-slate-400 tracking-tight">Routing Solver</h1>
          <p className="text-slate-400 text-sm mt-1.5 font-medium">Configure and dispatch AI constraint solvers</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        
        {/* Controls Engine */}
        <motion.div variants={itemVariants} className="glass-card p-6 flex flex-col gap-6 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/5 blur-[80px] rounded-full point-events-none" />
          
          <div>
            <h3 className="section-title flex items-center gap-2">
              <span className="w-5 h-5 rounded-full bg-slate-800 flex items-center justify-center text-[10px] text-white">1</span> 
              Semantic Clustering
            </h3>
            <p className="text-[13px] text-slate-400 mb-4 leading-relaxed font-medium">Spatio-temporal grouping before running the heavy TSP/VRP solvers.</p>
            <motion.button 
              whileTap={{ scale: 0.98 }}
              onClick={() => clusterMutation.mutate()} disabled={clusterMutation.isLoading}
              className="btn-secondary w-full"
            >
              {clusterMutation.isLoading ? <Loader2 className="w-4 h-4 animate-spin text-indigo-400" /> : <Network className="w-4 h-4 text-indigo-400" />}
              Generate Clusters
            </motion.button>
          </div>

          <div className="border-t border-white/5 pt-6">
            <h3 className="section-title flex items-center gap-2">
              <span className="w-5 h-5 rounded-full bg-slate-800 flex items-center justify-center text-[10px] text-white">2</span> 
              Algorithm Selection
            </h3>
            <div className="space-y-3 mt-4">
              {algos.map(a => (
                <button key={a.id} id={`algo-${a.id}`}
                  onClick={() => setAlgorithm(a.id as any)}
                  className={`w-full p-4 rounded-xl text-left transition-all ${
                    algorithm === a.id
                      ? 'bg-indigo-500/10 border border-indigo-500/30 shadow-[0_4px_15px_rgba(99,102,241,0.1)]'
                      : 'bg-[#1e293b]/50 border border-white/5 hover:border-white/10 hover:bg-[#1e293b]'
                  }`}>
                  <div className="flex items-center gap-3">
                    <span className="text-lg">{a.icon}</span>
                    <div>
                      <div className={`text-sm font-bold ${algorithm === a.id ? 'text-indigo-300' : 'text-slate-200'}`}>{a.label}</div>
                      <div className="text-[11px] text-slate-500 mt-0.5 font-medium">{a.desc}</div>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>

          <div className="border-t border-white/5 pt-6 mt-auto">
             <motion.button 
              whileTap={{ scale: 0.98 }}
              onClick={() => optimizeMutation.mutate()} disabled={optimizeMutation.isLoading}
              className="btn-primary w-full py-3.5 text-base relative overflow-hidden group"
            >
              <div className="absolute inset-0 bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity" />
              {optimizeMutation.isLoading
                ? <><Loader2 className="w-5 h-5 animate-spin" /> Solving constraints...</>
                : <><Zap className="w-5 h-5 text-amber-300" /> Dispatch Solver</>}
            </motion.button>
          </div>
        </motion.div>

        {/* Results Canvas */}
        <div className="lg:col-span-2 space-y-6 flex flex-col">
          
          {/* Top level metrics */}
          {carbon && (
            <motion.div variants={itemVariants} className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[
                { label: 'Projected Carbon Mitigation', value: `${carbon.co2_saved_kg?.toFixed(0)} kg`, color: '#10b981', bg: 'bg-emerald-500/10', border: 'border-emerald-500/20' },
                { label: 'Total Residual Footprint', value: `${carbon.total_co2_kg?.toFixed(0)} kg`, color: '#f43f5e', bg: 'bg-rose-500/10', border: 'border-rose-500/20' },
                { label: 'Net Efficiency Delta', value: `${carbon.co2_reduction_percent}%`, color: '#6366f1', bg: 'bg-indigo-500/10', border: 'border-indigo-500/20' },
              ].map(({ label, value, color, bg, border }) => (
                <div key={label} className={`glass-card p-5 border ${border}`}>
                  <div className={`text-2xl font-black mb-1`} style={{ color }}>{value}</div>
                  <div className="text-xs text-slate-400 font-medium uppercase tracking-wider">{label}</div>
                </div>
              ))}
            </motion.div>
          )}

          {/* Visualization */}
          <motion.div variants={itemVariants} className="glass-card p-6 flex-1 min-h-[300px] flex flex-col">
            <h3 className="section-title">Capacity Allocation via Solver</h3>
            {routeData.length > 0 ? (
              <div className="flex-1 mt-4">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={routeData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                    <CartesianGrid vertical={false} stroke="rgba(255,255,255,0.02)" />
                    <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} dy={10} />
                    <YAxis domain={[0, 100]} tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={v => `${v}%`} />
                    <Tooltip formatter={(v: any) => [`${v}%`, 'Capacity Used']} cursor={{ fill: 'rgba(255,255,255,0.02)' }} />
                    <Bar dataKey="utilization" radius={[6, 6, 0, 0]} animationDuration={1500}>
                      {routeData.map((entry: any, i: number) => (
                        <Cell key={i} fill={entry.utilization >= 85 ? '#10b981' : entry.utilization >= 60 ? '#8b5cf6' : '#f43f5e'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="flex-1 flex items-center justify-center text-slate-500 text-sm font-medium">
                No solver runs recorded. Dispatch solver to view allocations.
              </div>
            )}
          </motion.div>

        </div>
      </div>
      
      {/* Routes Table */}
      {(routes || []).length > 0 && (
        <motion.div variants={itemVariants} className="glass-card overflow-hidden">
          <div className="p-6 border-b border-white/5 flex items-center justify-between">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">Generated Route Manifest</h3>
            <div className="badge badge-blue">{(routes || []).length} Routes Active</div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="bg-[#1e293b]/50 border-b border-white/5">
                <tr>
                  <th className="py-3 px-6 text-[11px] font-bold text-slate-400 uppercase tracking-wider">Route ID</th>
                  <th className="py-3 px-6 text-[11px] font-bold text-slate-400 uppercase tracking-wider">Assigned Fleet Asset</th>
                  <th className="py-3 px-6 text-[11px] font-bold text-slate-400 uppercase tracking-wider">Drop Counts</th>
                  <th className="py-3 px-6 text-[11px] font-bold text-slate-400 uppercase tracking-wider">Est. Path (km)</th>
                  <th className="py-3 px-6 text-[11px] font-bold text-slate-400 uppercase tracking-wider">Transport Cost</th>
                  <th className="py-3 px-6 text-[11px] font-bold text-slate-400 uppercase tracking-wider">Capacity Fill</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {(routes || []).slice(0, 20).map((r: any, i: number) => (
                  <tr key={r.route_id || i} className="hover:bg-white/5 transition-colors">
                    <td className="py-3 px-6 text-slate-300 font-mono text-xs">RT-{String(i + 1).padStart(3, '0')}</td>
                    <td className="py-3 px-6 text-indigo-300 font-mono text-xs">{(r.vehicle_id || 'UNKNOWN').slice(0, 8)}</td>
                    <td className="py-3 px-6 text-white font-medium">{(r.shipment_ids || []).length} units</td>
                    <td className="py-3 px-6 text-slate-400">{(r.total_distance || 0).toFixed(1)} km</td>
                    <td className="py-3 px-6 text-emerald-400 font-mono">₹{(r.total_cost || 0).toLocaleString()}</td>
                    <td className="py-3 px-6">
                      <span className={`badge ${(r.utilization_percent || 0) >= 80 ? 'badge-green' : (r.utilization_percent || 0) >= 60 ? 'badge-purple' : 'badge-red'}`}>
                        {(r.utilization_percent || 0).toFixed(0)}% Fill
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>
      )}

    </motion.div>
  );
}
