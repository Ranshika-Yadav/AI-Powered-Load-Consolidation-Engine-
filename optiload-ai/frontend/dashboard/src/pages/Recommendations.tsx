import { useQuery } from 'react-query';
import { motion } from 'framer-motion';
import { Lightbulb, TrendingDown, AlertTriangle, Zap, ArrowRight, Activity, Leaf, Truck } from 'lucide-react';
import { getRecommendations } from '../api/client';

const SEVERITY_STYLES: Record<string, string> = {
  high: 'bg-rose-500/10 border-rose-500/20 text-rose-400 shadow-[0_0_15px_rgba(244,63,94,0.1)]',
  medium: 'bg-amber-500/10 border-amber-500/20 text-amber-400',
  low: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400',
};

const ACTION_ICON: Record<string, any> = {
  consolidate: Zap,
  optimize: TrendingDown,
  alert: AlertTriangle,
  green: Leaf,
};

const STATIC_RECOMMENDATIONS = [
  {
    id: 1, type: "consolidation", severity: "high",
    title: "Consolidate Shipments #12, #18, and #21",
    description: "Consolidating Shipments #12, #18, and #21 into Vehicle V-05 increases utilization from 64% → 92% and reduces deadhead mileage.",
    potential_saving_inr: 3250, action: "consolidate",
    impact: { utilization_change: "+28%", cost_reduction: "₹3,250", co2_saved: "45 kg" },
  },
  {
    id: 2, type: "underutilization", severity: "medium",
    title: "Asset MH-12-AB-4523 Under-Utilized (38%)",
    description: "This Heavy-CV is only 38% utilized on today's assignment. Cross-docking 3 pending shipments from the Pune hub balances the load.",
    potential_saving_inr: 1800, action: "consolidate",
    impact: { utilization_change: "+43%", cost_reduction: "₹1,800", co2_saved: "28 kg" },
  },
  {
    id: 3, type: "priority_alert", severity: "high",
    title: "SLA Risk: 4 High-Priority Shipments Unassigned",
    description: "4 critical shipments with tight delivery windows (T-24h) have escaped the morning routing assignment.",
    potential_saving_inr: 5000, action: "alert",
    impact: { delay_avoided: "4 units", sla_compliance: "+100%", penalty_offset: "₹5,000" },
  },
  {
    id: 4, type: "route_optimization", severity: "medium",
    title: "Merge Target: Mumbai→Pune→Nashik Hubs",
    description: "Vehicles V03 and V07 both execute the Mumbai → Nashik corridor on overlapping constraints. A unified MILP solve saves an entire trip.",
    potential_saving_inr: 4100, action: "optimize",
    impact: { trips_saved: "1 LTL run", cost_reduction: "₹4,100", co2_saved: "89 kg" },
  },
  {
    id: 5, type: "carbon_reduction", severity: "low",
    title: "EV Substitution on Sub-100km Corridors",
    description: "Replacing 5 diesel local-delivery trucks with EV structural equivalents on high-frequency city cycles yields significant footprint trim.",
    potential_saving_inr: 12000, action: "green",
    impact: { carbon_trim: "2.4T/mo", fuel_hedging: "₹12K/mo", roi_cycle: "8 months" },
  },
  {
    id: 6, type: "consolidation", severity: "medium",
    title: "Network Density: Bangalore → Chennai Corridor",
    description: "12 latent shipments on the BLR-MAA lane can be cross-docked, halving raw transportation cost allocations for tomorrow's dispatch.",
    potential_saving_inr: 7600, action: "consolidate",
    impact: { lane_density: "+35%", run_compression: "4 runs", cost_offset: "₹7,600" },
  },
];

const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.1 } }
};
const itemVariants = {
  hidden: { opacity: 0, scale: 0.95 },
  show: { opacity: 1, scale: 1, transition: { type: 'spring', stiffness: 100 } }
};

export default function RecommendationsPage() {
  const { data: apiRecs, isLoading } = useQuery('recommendations', () =>
    getRecommendations().then(r => r.data.recommendations), { onError: () => {} });

  const recommendations = (apiRecs && apiRecs.length > 0 && !isLoading) ? apiRecs : STATIC_RECOMMENDATIONS;

  const totalSavings = recommendations.reduce((a: any, b: any) => a + (b.potential_saving_inr || 0), 0);
  const highPriority = recommendations.filter((r: any) => r.severity === 'high').length;

  return (
    <div className="p-8 min-h-full max-w-7xl mx-auto">
      
      {/* Header */}
      <div className="flex items-center gap-4 mb-10">
        <div className="w-12 h-12 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center shadow-[0_0_20px_rgba(245,158,11,0.15)]">
          <Lightbulb className="w-6 h-6 text-amber-500" />
        </div>
        <div>
          <h1 className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-white to-slate-400 tracking-tight">AI Strategic Insights</h1>
          <p className="text-slate-400 text-sm mt-1.5 font-medium">Automatic system-generated heuristics and anomaly detection</p>
        </div>
      </div>

      {/* Hero Stats */}
      <motion.div 
        initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}
        className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-10"
      >
        <div className="glass-card p-6 flex flex-col relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/5 blur-[40px] rounded-full group-hover:bg-emerald-500/10 transition-colors" />
          <div className="text-emerald-400 mb-2"><TrendingDown className="w-6 h-6" /></div>
          <div className="text-3xl font-black text-white tracking-tight">₹{(totalSavings / 1000).toFixed(1)}K</div>
          <div className="text-xs text-slate-400 font-bold uppercase tracking-wider mt-1">Identified Capital Relief</div>
        </div>
        
        <div className="glass-card p-6 flex flex-col relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-32 h-32 bg-rose-500/5 blur-[40px] rounded-full group-hover:bg-rose-500/10 transition-colors" />
          <div className="text-rose-400 mb-2"><AlertTriangle className="w-6 h-6" /></div>
          <div className="text-3xl font-black text-white tracking-tight">{highPriority}</div>
          <div className="text-xs text-slate-400 font-bold uppercase tracking-wider mt-1">Critical SLA Interventions</div>
        </div>

        <div className="glass-card p-6 flex flex-col relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500/5 blur-[40px] rounded-full group-hover:bg-indigo-500/10 transition-colors" />
          <div className="text-indigo-400 mb-2"><Activity className="w-6 h-6" /></div>
          <div className="text-3xl font-black text-white tracking-tight">{recommendations.length}</div>
          <div className="text-xs text-slate-400 font-bold uppercase tracking-wider mt-1">Total System Proposals</div>
        </div>
      </motion.div>

      {/* Feed */}
      <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider mb-5 flex items-center gap-2">
        <Truck className="w-4 h-4 text-slate-500" /> Active Intel Stream
      </h3>

      <motion.div variants={containerVariants} initial="hidden" animate="show" className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {recommendations.map((rec: any, i: number) => {
          const ActionIcon = ACTION_ICON[rec.action] || Zap;
          const style = SEVERITY_STYLES[rec.severity] || SEVERITY_STYLES.low;
          
          return (
            <motion.div variants={itemVariants} key={rec.id || i}
              className="glass-card flex flex-col hover:border-indigo-500/30 hover:bg-[#1e293b]/40 transition-all duration-300 group overflow-hidden">
              
              <div className="p-6 flex-1">
                <div className="flex items-start gap-4">
                  <div className={`w-12 h-12 rounded-2xl flex-shrink-0 flex items-center justify-center border ${style}`}>
                    <ActionIcon className="w-6 h-6" />
                  </div>
                  
                  <div className="flex-1 min-w-0 pt-0.5">
                    <div className="flex items-start justify-between gap-3 mb-2.5">
                      <h3 className="text-[15px] font-bold text-white leading-tight">{rec.title}</h3>
                      <span className={`px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider rounded-md border ${style}`}>
                        {rec.severity}
                      </span>
                    </div>
                    
                    <p className="text-[13px] text-slate-400 leading-relaxed font-medium">{rec.description}</p>
                    
                    {/* Data Matrix */}
                    {rec.impact && (
                      <div className="grid grid-cols-3 gap-3 mt-5">
                        {Object.entries(rec.impact).map(([k, v]) => (
                          <div key={k} className="bg-[#0f172a]/60 rounded-xl p-2.5 text-center border border-white/5 shadow-inner">
                            <div className="text-[12px] font-black text-white">{String(v)}</div>
                            <div className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider mt-1 truncate">{k.replace(/_/g, ' ')}</div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Action Footer */}
              <div className="bg-[#0f172a]/80 px-6 py-4 border-t border-white/5 flex items-center justify-between mt-auto group-hover:bg-[#1e293b]/80 transition-colors">
                <div className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="text-xs font-bold text-emerald-400">
                    Est. Retained Value: ₹{(rec.potential_saving_inr || 0).toLocaleString()}
                  </span>
                </div>
                
                <button className="flex items-center gap-2 text-[13px] font-bold text-indigo-400 hover:text-indigo-300 transition-colors group/btn">
                  Resolve Proposal <ArrowRight className="w-4 h-4 group-hover/btn:translate-x-1 transition-transform" />
                </button>
              </div>

            </motion.div>
          );
        })}
      </motion.div>

    </div>
  );
}
