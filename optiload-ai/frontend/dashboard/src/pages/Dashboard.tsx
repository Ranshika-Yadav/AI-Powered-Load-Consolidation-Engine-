import { useState, useEffect } from 'react';
import { useQuery } from 'react-query';
import { motion, animate, useMotionValue, useTransform } from 'framer-motion';
import { 
  BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Area, AreaChart, Cell
} from 'recharts';
import { 
  Package, Truck, TrendingDown, RefreshCw, AlertTriangle, 
  ArrowUpRight, ArrowDownRight, Zap, Download, ChevronRight, CheckCircle2,
  Clock, Route, Activity
} from 'lucide-react';
import CountUp from 'react-countup';
import { getDashboardMetrics, loadDemoData } from '../api/client';
import toast from 'react-hot-toast';

// --- KPI Card Component ---
function KpiCard({ title, value, prefix, suffix, formatter, subtitle, icon: Icon, color, trend, trendVal }: any) {
  return (
    <motion.div 
      variants={{ hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }} 
      className="bg-[#0f172a] border border-white/10 rounded-2xl p-6 hover:shadow-xl hover:-translate-y-1 transition-all group"
    >
      <div className="flex items-start justify-between mb-4">
        <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-gray-800">
          <Icon className="w-5 h-5 text-gray-300 group-hover:text-indigo-400 transition-colors" />
        </div>
        {trendVal && (
          <div className="flex items-center gap-1 text-[12px] font-medium text-emerald-400 bg-emerald-400/10 px-2 py-1 rounded-full">
            <ArrowUpRight className="w-3 h-3" />
            {trendVal}
          </div>
        )}
      </div>
      
      <div>
        <div className="text-3xl font-bold text-white mb-1 flex items-end tracking-tight">
          {prefix && <span className="text-xl text-gray-400 mb-0.5">{prefix}</span>}
          <CountUp
             end={Number(value)}
             duration={2}
             separator=","
             decimals={value % 1 !== 0 ? 1 : 0}
          />
          {suffix && <span className="text-lg text-gray-400 ml-1 mb-0.5">{suffix}</span>}
        </div>
        <div className="text-sm font-medium text-gray-400">{title}</div>
      </div>
    </motion.div>
  );
}

// --- Main Dashboard Page ---
export default function DashboardPage() {
  const [loadingDemo, setLoadingDemo] = useState(false);
  
  const { data, isLoading, refetch } = useQuery('dashboard-metrics', 
    () => getDashboardMetrics().then(r => r.data), {
    refetchInterval: 30000,
    onError: () => {},
  });

  const handleLoadDemo = async () => {
    setLoadingDemo(true);
    try {
      await loadDemoData();
      toast.success('System initialized with demo dataset.', { style: { background: '#0f172a', color: '#fff', border: '1px solid rgba(255,255,255,0.1)' }});
      setTimeout(() => refetch(), 1000);
    } catch {
      toast.error('Initialization failed. Check services.');
    } finally {
      setLoadingDemo(false);
    }
  };

  const kpis = data ? [
    {
      title: 'Total Shipments',
      value: data.shipments.total,
      suffix: '',
      icon: Package,
      trendVal: '12% this week',
    },
    {
      title: 'Fleet Utilization',
      value: data.vehicles.avg_utilization_percent,
      suffix: '%',
      formatter: (v: number) => v.toFixed(1),
      icon: Truck,
      trendVal: '8% this week',
    },
    {
      title: 'Trips Saved',
      value: data.optimization.trips_saved || 0,
      suffix: '',
      icon: Route,
      trendVal: 'Improved',
    },
    {
      title: 'Cost Savings',
      value: data.optimization.cost_savings_inr || 0,
      prefix: '₹',
      suffix: '',
      icon: TrendingDown,
      trendVal: 'Consistent',
    },
  ] : [];

  const trendData = (data?.cost_trend || []).map((d: any) => ({
    name: d.date.slice(-5), // mm-dd
    cost: d.cost,
    utilization: Math.min(100, Math.max(60, 100 - (d.cost % 30))) // Mocking utilization trend matching cost structure
  }));

  const utilDist = (data?.utilization_distribution || []).map((v: number, i: number) => ({
    name: `V${String(i+1).padStart(2, '0')}`,
    eff: Math.round(v)
  }));

  return (
    <div className="p-6 lg:p-10 min-h-full max-w-[1400px] mx-auto overflow-x-hidden text-slate-200">
      
      {/* ── Page Header ── */}
      <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col sm:flex-row sm:items-center justify-between mb-8 gap-5 relative z-20">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white mb-1">
            Dashboard Title
          </h1>
          <p className="text-gray-400 text-sm font-medium">
            Overview of your fleet logistics, optimizations, and performance.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button 
            onClick={handleLoadDemo} disabled={loadingDemo}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-gradient-to-r from-indigo-500 to-purple-500 rounded-xl hover:scale-105 active:scale-95 transition-all shadow-md focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
          >
            {loadingDemo ? <RefreshCw className="w-4 h-4 animate-spin text-white" /> : <Zap className="w-4 h-4 text-white" />}
            {loadingDemo ? 'Simulating...' : 'Load Demo Data'}
          </button>
          <button 
            onClick={() => refetch()} 
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-gray-800 border border-white/10 rounded-xl hover:scale-105 active:scale-95 transition-all focus:outline-none focus:ring-2 focus:ring-gray-600"
          >
            <RefreshCw className="w-4 h-4" /> Refresh
          </button>
        </div>
      </motion.div>

      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-[#0f172a] border border-white/10 p-6 h-36 rounded-2xl animate-pulse">
              <div className="w-10 h-10 bg-gray-800 rounded-lg mb-4" />
              <div className="w-24 h-8 bg-gray-800 rounded-md mb-2" />
              <div className="w-32 h-4 bg-gray-800 rounded-md" />
            </div>
          ))}
        </div>
      ) : (
        <motion.div variants={{ show: { transition: { staggerChildren: 0.08 } } }} initial="hidden" animate="show">
          
          <h2 className="text-lg font-semibold text-white mb-4 mt-6">Key Metrics</h2>

          {/* ── KPI Grid ── */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
            {kpis.map((kpi, i) => <KpiCard key={i} {...kpi} />)}
          </div>

          <h2 className="text-lg font-semibold text-white mb-4">Analytics</h2>

          {/* ── Analytics Charts row ── */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-10">
            
            {/* Fleet Utilization Trend */}
            <motion.div variants={{ hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }} className="bg-[#0f172a] border border-white/10 rounded-2xl p-6 hover:shadow-xl transition-shadow">
              <h3 className="text-sm font-semibold text-gray-300 mb-6 flex items-center gap-2">
                <Activity className="w-4 h-4 text-indigo-400" /> Fleet Utilization Trend
              </h3>
              {trendData.length > 0 ? (
                <div className="h-[280px] w-full mt-2">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={trendData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                      <defs>
                        <linearGradient id="colorUtil" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#6366f1" stopOpacity={0.2} />
                          <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid vertical={false} stroke="rgba(255,255,255,0.05)" strokeDasharray="3 3" />
                      <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 12 }} axisLine={false} tickLine={false} dy={10} />
                      <YAxis tick={{ fill: '#9ca3af', fontSize: 12 }} axisLine={false} tickLine={false} tickFormatter={v => `${v}%`} />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff' }}
                        itemStyle={{ color: '#818cf8', fontWeight: 600 }} cursor={{ stroke: 'rgba(255,255,255,0.1)', strokeWidth: 1 }}
                      />
                      <Area type="monotone" dataKey="utilization" stroke="#818cf8" strokeWidth={2} fillOpacity={1} fill="url(#colorUtil)" animationDuration={1000} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-[280px] flex items-center justify-center">
                  <div className="text-center">
                    <AlertTriangle className="w-6 h-6 mx-auto mb-2 text-gray-500" />
                    <div className="text-sm text-gray-400">No utilization data available</div>
                  </div>
                </div>
              )}
            </motion.div>

            {/* Optimization Efficiency */}
            <motion.div variants={{ hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }} className="bg-[#0f172a] border border-white/10 rounded-2xl p-6 hover:shadow-xl transition-shadow">
              <h3 className="text-sm font-semibold text-gray-300 mb-6 flex items-center gap-2">
                <Zap className="w-4 h-4 text-purple-400" /> Optimization Efficiency
              </h3>
              {utilDist.length > 0 ? (
                <div className="h-[280px] w-full mt-2">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={utilDist.slice(0, 15)} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                      <CartesianGrid vertical={false} stroke="rgba(255,255,255,0.05)" strokeDasharray="3 3" />
                      <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 12 }} axisLine={false} tickLine={false} dy={10} />
                      <YAxis tick={{ fill: '#9ca3af', fontSize: 12 }} axisLine={false} tickLine={false} tickFormatter={v => `${v}%`} />
                      <Tooltip 
                        cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                        contentStyle={{ backgroundColor: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff' }}
                        itemStyle={{ color: '#fff', fontWeight: 600 }}
                      />
                      <Bar dataKey="eff" radius={[4, 4, 0, 0]} animationDuration={1000} fill="#c084fc">
                        {utilDist.map((entry: any, index: number) => (
                          <Cell key={`cell-${index}`} fill={entry.eff > 85 ? '#818cf8' : entry.eff > 65 ? '#a78bfa' : '#c084fc'} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-[280px] flex items-center justify-center">
                  <div className="text-center">
                    <AlertTriangle className="w-6 h-6 mx-auto mb-2 text-gray-500" />
                    <div className="text-sm text-gray-400">Waiting for solver outputs</div>
                  </div>
                </div>
              )}
            </motion.div>
          </div>

          <h2 className="text-lg font-semibold text-white mb-4">Insights & Activity</h2>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-10">
            {/* ── Optimization Results ── */}
            <motion.div 
              variants={{ hidden: { opacity: 0, x: -20 }, show: { opacity: 1, x: 0 } }} 
              className="bg-[#0f172a] border border-white/10 rounded-2xl p-6 lg:p-8 hover:shadow-xl transition-shadow flex flex-col justify-between gap-6"
            >
              <div className="space-y-5">
                <div>
                  <h3 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
                    <Zap className="w-4 h-4 text-indigo-400" /> Latest Optimization
                  </h3>
                  <p className="text-xs text-gray-500 mt-1">
                    AI generated cluster assignments vs standard baseline routes.
                  </p>
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <div className="text-[10px] uppercase tracking-wider font-bold text-gray-500 mb-1">Trips Saved</div>
                    <div className="text-2xl font-bold text-white tracking-tight">{data?.optimization.trips_saved || 0}</div>
                  </div>
                  <div>
                    <div className="text-[10px] uppercase tracking-wider font-bold text-gray-500 mb-1">Distance</div>
                    <div className="text-2xl font-bold text-white tracking-tight">-{data?.optimization.cost_reduction_percent || 0}%</div>
                  </div>
                  <div>
                    <div className="text-[10px] uppercase tracking-wider font-bold text-gray-500 mb-1">Cost Saved</div>
                    <div className="text-2xl font-bold text-emerald-400 tracking-tight">₹{(data?.optimization.cost_savings_inr || 0).toLocaleString()}</div>
                  </div>
                </div>
              </div>

              <div className="flex gap-3 mt-4">
                <button className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-500 hover:bg-indigo-600 text-white text-xs font-bold rounded-xl transition-colors focus:ring-2 focus:ring-indigo-400">
                  View Routes
                </button>
                <button className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-gray-800 hover:bg-gray-700 border border-white/10 text-white text-xs font-bold rounded-xl transition-colors focus:ring-2 focus:ring-gray-600">
                  <Download className="w-4 h-4" /> Report
                </button>
              </div>
            </motion.div>

            {/* ── Recent Activity / System Log ── */}
            <motion.div 
              variants={{ hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }} 
              className="bg-[#0f172a] border border-white/10 rounded-2xl p-6 hover:shadow-xl transition-shadow"
            >
              <h3 className="text-sm font-semibold text-gray-300 mb-6 flex items-center gap-2">
                <Clock className="w-4 h-4 text-gray-400" /> Recent Activity
              </h3>
              
              <div className="space-y-4">
                {[
                  { title: "Route A optimized", saved: "Saved 15 km", time: "2m ago" },
                  { title: "Route B optimized", saved: "Saved ₹2500", time: "45m ago" },
                  { title: "Fleet re-allocation", saved: "+8% eff", time: "3h ago" },
                  { title: "Synthesis batch", saved: "Success", time: "1d ago" },
                ].map((log, i) => (
                  <div key={i} className="flex gap-4 items-start pb-4 border-b border-white/5 last:border-0 last:pb-0">
                    <div className="mt-1 bg-gray-800 p-1.5 rounded-lg border border-white/5 shrink-0">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    </div>
                    <div className="flex-1 flex items-center justify-between">
                      <div>
                        <div className="text-[13px] font-bold text-white mb-1">{log.title}</div>
                        <div className="text-xs text-emerald-400 font-medium">{log.saved}</div>
                      </div>
                      <div className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">{log.time}</div>
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          </div>

        </motion.div>
      )}
    </div>
  );
}
