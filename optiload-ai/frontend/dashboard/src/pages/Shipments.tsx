import { useState } from 'react';
import { useQuery } from 'react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { Package, Search, Upload, Loader2, ArrowUpDown } from 'lucide-react';
import { getShipments, uploadShipments } from '../api/client';
import toast from 'react-hot-toast';

const STATUS_COLORS: Record<string, string> = {
  pending: 'badge-amber',
  optimized: 'badge-green',
  delivered: 'badge-blue',
  failed: 'badge-red',
};

const PRIORITY_LABELS: Record<number, { label: string; class: string }> = {
  1: { label: 'Low', class: 'badge-blue' },
  2: { label: 'Normal', class: 'badge-blue' },
  3: { label: 'Medium', class: 'badge-amber' },
  4: { label: 'High', class: 'badge-red' },
  5: { label: 'Urgent', class: 'badge-red' },
};

const pageVariants = {
  hidden: { opacity: 0, y: 15 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: 'easeOut' } }
};

export default function ShipmentsPage() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [uploading, setUploading] = useState(false);

  const { data: shipments, isLoading, refetch } = useQuery('shipments',
    () => getShipments(200).then(r => r.data), { onError: () => {} });

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const res = await uploadShipments(file);
      toast.success(`Uploaded ${res.data.success_count} shipments!`);
      if (res.data.failed_count > 0) toast.error(`${res.data.failed_count} rows failed validation`);
      refetch();
    } catch {
      toast.error('Upload failed');
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const filtered = (shipments || []).filter((s: any) => {
    const matchSearch = !search || 
      s.shipment_id?.toLowerCase().includes(search.toLowerCase()) ||
      s.origin_city?.toLowerCase().includes(search.toLowerCase()) ||
      s.destination_city?.toLowerCase().includes(search.toLowerCase());
    const matchStatus = statusFilter === 'all' || s.status === statusFilter;
    return matchSearch && matchStatus;
  });

  return (
    <motion.div variants={pageVariants} initial="hidden" animate="visible" className="p-8 min-h-full max-w-7xl mx-auto">
      
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between mb-8 gap-4">
        <div>
          <h1 className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-white to-slate-400 tracking-tight">Shipments Registry</h1>
          <p className="text-slate-400 text-sm mt-1.5 font-medium">Manage and track your entire logistics pipeline</p>
        </div>
        
        <motion.label whileTap={{ scale: 0.95 }} id="upload-btn" className="btn-primary cursor-pointer relative overflow-hidden group">
          <div className="absolute inset-0 bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity" />
          {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
          Import CSV Dataset
          <input type="file" accept=".csv" className="hidden" onChange={handleUpload} disabled={uploading} />
        </motion.label>
      </div>

      {/* Control Bar */}
      <div className="glass-card p-2 pl-4 mb-6 flex flex-col md:flex-row gap-4 items-center justify-between">
        <div className="relative flex-1 w-full max-w-sm">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input 
            type="text" placeholder="Search PO numbers, cities..." value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full bg-transparent border-none text-white placeholder-slate-500 text-sm py-2 pl-9 focus:outline-none focus:ring-0" 
          />
        </div>
        
        <div className="flex items-center gap-2 pr-2">
          <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Status</span>
          <select 
            value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
            className="bg-[#1e293b] border border-white/10 text-white text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:border-indigo-500 cursor-pointer"
          >
            <option value="all">All</option>
            <option value="pending">Pending</option>
            <option value="optimized">Optimized</option>
            <option value="delivered">Delivered</option>
          </select>
        </div>
      </div>

      {/* Data Table */}
      <div className="glass-card overflow-hidden">
        {isLoading ? (
          <div className="p-16 flex flex-col items-center justify-center">
            <Loader2 className="w-8 h-8 animate-spin text-indigo-500 mb-4" />
            <div className="text-sm text-slate-400 font-medium">Fetching registry data...</div>
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-16 text-center text-slate-500 flex flex-col items-center">
            <div className="w-16 h-16 bg-slate-800/50 rounded-2xl flex items-center justify-center mb-4 border border-white/5">
              <Package className="w-8 h-8 text-slate-400" />
            </div>
            <p className="text-sm font-medium text-slate-300">No shipments found</p>
            <p className="text-xs mt-1">Import a CSV or adjust your search filters.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="bg-slate-900/50 border-b border-white/5">
                <tr>
                  {['Identifier', 'Origin Node', 'Destination Node', 'Weight', 'Vol.', 'Target Date', 'Priority', 'Status'].map(h => (
                    <th key={h} className="py-4 px-5 text-[11px] font-bold text-slate-400 uppercase tracking-wider whitespace-nowrap">
                      <div className="flex items-center gap-1.5">
                        {h} {h !== 'Status' && <ArrowUpDown className="w-3 h-3 opacity-30" />}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                <AnimatePresence>
                  {filtered.slice(0, 100).map((s: any, i: number) => (
                    <motion.tr 
                      key={s.shipment_id || i}
                      initial={{ opacity: 0, y: 10 }} 
                      animate={{ opacity: 1, y: 0 }} 
                      exit={{ opacity: 0, scale: 0.95 }}
                      transition={{ delay: Math.min(i * 0.02, 0.2) }}
                      className="hover:bg-indigo-500/5 transition-colors group cursor-default"
                    >
                      <td className="py-4 px-5 font-mono text-[13px] text-slate-400 group-hover:text-indigo-300 transition-colors">
                        {(s.shipment_id || '').slice(0, 8)}
                      </td>
                      <td className="py-4 px-5 font-medium text-white">{s.origin_city || `${s.origin_lat?.toFixed(2)}`}</td>
                      <td className="py-4 px-5 font-medium text-white">{s.destination_city || `${s.destination_lat?.toFixed(2)}`}</td>
                      <td className="py-4 px-5 text-slate-400">{(s.weight || 0).toLocaleString()} kg</td>
                      <td className="py-4 px-5 text-slate-400">{(s.volume || 0).toFixed(1)} m³</td>
                      <td className="py-4 px-5 text-slate-400 text-[13px]">{s.pickup_time ? new Date(s.pickup_time).toLocaleDateString() : '—'}</td>
                      <td className="py-4 px-5">
                        <span className={`badge ${PRIORITY_LABELS[s.priority]?.class || 'badge-blue'}`}>
                          {PRIORITY_LABELS[s.priority]?.label || `P${s.priority}`}
                        </span>
                      </td>
                      <td className="py-4 px-5">
                        <div className="flex items-center gap-2">
                          <div className={`w-1.5 h-1.5 rounded-full ${s.status === 'optimized' ? 'bg-emerald-400' : s.status === 'delivered' ? 'bg-indigo-400' : 'bg-amber-400'}`} />
                          <span className={`badge ${STATUS_COLORS[s.status] || 'badge-blue'}`}>
                            {s.status}
                          </span>
                        </div>
                      </td>
                    </motion.tr>
                  ))}
                </AnimatePresence>
              </tbody>
            </table>
          </div>
        )}
      </div>
    </motion.div>
  );
}
