import { useState } from 'react';
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  LayoutDashboard, Map, Package, Zap, FlaskConical, 
  Lightbulb, LogOut, Truck, Activity, ChevronLeft, ChevronRight, Menu, Bell, User, Settings
} from 'lucide-react';
import toast from 'react-hot-toast';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

// Utility for cleaner class merging
function cn(...inputs: (string | undefined | null | false)[]) {
  return twMerge(clsx(inputs));
}

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/map', icon: Map, label: 'Map View' },
  { to: '/shipments', icon: Package, label: 'Shipments' },
  { to: '/optimize', icon: Zap, label: 'Optimize' },
  { to: '/simulator', icon: FlaskConical, label: 'Simulator' },
  { to: '/recommendations', icon: Lightbulb, label: 'AI Insights' },
];

export default function Layout() {
  const navigate = useNavigate();
  const location = useLocation();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    toast.success('Logged out successfully', { style: { background: '#1e293b', color: '#fff' }});
    navigate('/login');
  };

  const activeRouteName = navItems.find(item => location.pathname.startsWith(item.to))?.label || 'Dashboard';

  const SidebarContent = () => (
    <>
      {/* Toggle Button (Desktop only) */}
      <button 
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="hidden md:flex absolute -right-3 top-8 bg-[#1e293b] border border-white/10 rounded-full p-1.5 text-slate-400 hover:text-white hover:bg-[#334155] shadow-lg transition-colors z-30"
      >
        {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
      </button>

      {/* Logo Section */}
      <div className="h-20 flex items-center px-6 border-b border-white/5 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 min-w-[36px] rounded-xl bg-gradient-to-br from-indigo-500 to-fuchsia-500 flex items-center justify-center shadow-[0_0_20px_rgba(99,102,241,0.3)]">
            <Truck className="w-5 h-5 text-white" />
          </div>
          <AnimatePresence mode="wait">
            {!isCollapsed && (
              <motion.div 
                initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -10 }} transition={{ duration: 0.2 }}
                className="flex flex-col whitespace-nowrap"
              >
                <span className="text-[17px] font-bold text-transparent bg-clip-text bg-gradient-to-r from-white to-slate-300 tracking-tight leading-tight">
                  OptiLoad AI
                </span>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-6 px-4 flex flex-col gap-1.5 overflow-y-auto no-scrollbar">
        <div className={cn("text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-3 pl-2", isCollapsed && "hidden")}>
          Platform
        </div>
        
        {navItems.map(({ to, icon: Icon, label }) => {
          const isActive = location.pathname.startsWith(to);
          return (
            <NavLink 
              key={to} to={to}
              onClick={() => setMobileMenuOpen(false)}
              className={cn(
                "relative group flex items-center px-3 py-2.5 rounded-xl transition-all duration-200",
                !isActive && "hover:bg-white/5"
              )}
            >
              {isActive && (
                <motion.div 
                  layoutId="activeNav"
                  className="absolute inset-0 bg-indigo-500/10 border border-indigo-500/20 rounded-xl"
                  initial={false} transition={{ type: "spring", stiffness: 300, damping: 30 }}
                />
              )}
              
              <div className={cn("relative flex items-center z-10 w-full", isCollapsed ? "justify-center" : "justify-start")}>
                <Icon className={cn("w-4 h-4 transition-colors duration-200", isActive ? "text-indigo-400" : "text-slate-400 group-hover:text-slate-200")} />
                
                <AnimatePresence mode="wait">
                  {!isCollapsed && (
                    <motion.span 
                      initial={{ opacity: 0, width: 0 }} animate={{ opacity: 1, width: 'auto' }} exit={{ opacity: 0, width: 0 }} transition={{ duration: 0.2 }}
                      className={cn("ml-3 text-[13px] font-bold whitespace-nowrap transition-colors", isActive ? "text-indigo-100" : "text-slate-400 group-hover:text-slate-200")}
                    >
                      {label}
                    </motion.span>
                  )}
                </AnimatePresence>
              </div>

              {/* Tooltip for collapsed state */}
              {isCollapsed && (
                <div className="absolute left-full ml-4 px-2 py-1 bg-[#1e293b] text-slate-200 text-xs font-semibold rounded-md opacity-0 group-hover:opacity-100 pointer-events-none z-50 transition-opacity whitespace-nowrap shadow-xl border border-white/10">
                  {label}
                </div>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Footer / System Status */}
      <div className="p-5 border-t border-white/5 shrink-0">
        <div className={cn("flex items-center p-3 rounded-xl bg-[#030712] border border-white/5 shadow-inner", isCollapsed ? "justify-center" : "justify-start gap-3")}>
          <div className="relative flex h-2 w-2 min-w-[8px]">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </div>
          {!isCollapsed && (
            <div className="flex flex-col">
              <span className="text-[11px] font-bold text-slate-300">All Systems Normal</span>
              <span className="text-[9px] text-slate-500 uppercase tracking-widest">Latency: 24ms</span>
            </div>
          )}
        </div>
      </div>
    </>
  );

  return (
    <div className="flex h-screen w-full bg-[#030712] text-slate-200 font-sans overflow-hidden selection:bg-indigo-500/30">
      
      {/* ── Desktop Sidebar ── */}
      <motion.aside 
        initial={{ width: 260 }} animate={{ width: isCollapsed ? 88 : 260 }} transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
        className="hidden md:flex relative flex-col h-full bg-[#0a0f1e]/80 backdrop-blur-3xl border-r border-white/5 z-20"
      >
        <SidebarContent />
      </motion.aside>

      {/* ── Mobile Sidebar Overlay ── */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <>
            <motion.div 
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={() => setMobileMenuOpen(false)}
              className="md:hidden fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
            />
            <motion.aside
              initial={{ x: -280 }} animate={{ x: 0 }} exit={{ x: -280 }} transition={{ type: "spring", bounce: 0, duration: 0.4 }}
              className="md:hidden fixed inset-y-0 left-0 w-[280px] bg-[#0a0f1e] border-r border-white/10 z-50 flex flex-col shadow-2xl"
            >
              <SidebarContent />
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      {/* ── Main Canvas ── */}
      <div className="flex-1 flex flex-col h-full overflow-hidden relative">
        
        {/* Subtle Background Glows */}
        <div className="absolute top-0 right-1/4 w-[500px] h-[500px] bg-indigo-500/5 blur-[120px] rounded-full pointer-events-none" />
        <div className="absolute bottom-0 left-1/4 w-[400px] h-[400px] bg-fuchsia-500/5 blur-[100px] rounded-full pointer-events-none" />

        {/* ── Top Header ── */}
        <header className="h-20 flex-shrink-0 flex items-center justify-between px-6 lg:px-10 border-b border-white/5 bg-[#0a0f1e]/60 backdrop-blur-2xl z-20 relative">
          <div className="flex items-center gap-4">
            <button onClick={() => setMobileMenuOpen(true)} className="md:hidden p-2 -ml-2 text-slate-400 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
              <Menu className="w-5 h-5" />
            </button>
            <h1 className="text-xl font-bold text-white tracking-tight">
              {activeRouteName}
            </h1>
          </div>

          <div className="flex items-center gap-3 sm:gap-5">
            <button className="p-2 text-slate-400 hover:text-white hover:bg-white/5 rounded-xl transition-all relative group">
              <Bell className="w-5 h-5 group-hover:scale-110 transition-transform" />
              <span className="absolute top-2 right-2.5 w-2 h-2 bg-rose-500 rounded-full border-2 border-[#0a0f1e]" />
            </button>
            
            <div className="w-px h-6 bg-white/10 hidden sm:block" />

            {/* User Profile Dropdown */}
            <div className="relative">
              <button 
                onClick={() => setDropdownOpen(!dropdownOpen)}
                className="flex items-center gap-3 p-1.5 pr-3 rounded-full hover:bg-white/5 border border-transparent hover:border-white/5 transition-all outline-none"
              >
                <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-indigo-600 to-fuchsia-600 flex items-center justify-center shadow-inner">
                  <User className="w-4 h-4 text-white" />
                </div>
                <div className="text-left hidden md:block">
                  <div className="text-[13px] font-bold text-slate-200 leading-none mb-1">Admin User</div>
                  <div className="text-[10px] text-slate-500 font-medium tracking-wide leading-none">admin@optiload.ai</div>
                </div>
              </button>
              
              <AnimatePresence>
                {dropdownOpen && (
                  <>
                    <div className="fixed inset-0 z-40" onClick={() => setDropdownOpen(false)} />
                    <motion.div 
                      initial={{ opacity: 0, y: 10, scale: 0.95 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: 10, scale: 0.95 }}
                      transition={{ duration: 0.2 }}
                      className="absolute right-0 mt-2 w-56 bg-[#0f172a] border border-white/10 rounded-2xl shadow-2xl overflow-hidden z-50 p-2"
                    >
                      <div className="px-3 py-2 mb-2 border-b border-white/5 md:hidden">
                        <div className="text-sm font-bold text-white">Admin User</div>
                        <div className="text-xs text-slate-400">admin@optiload.ai</div>
                      </div>
                      
                      <button className="w-full flex items-center gap-3 px-3 py-2.5 text-sm font-medium text-slate-300 hover:text-white hover:bg-white/5 rounded-xl transition-colors">
                        <User className="w-4 h-4" /> Profile
                      </button>
                      <button className="w-full flex items-center gap-3 px-3 py-2.5 text-sm font-medium text-slate-300 hover:text-white hover:bg-white/5 rounded-xl transition-colors">
                        <Settings className="w-4 h-4" /> Settings
                      </button>
                      <div className="h-px bg-white/5 my-2" />
                      <button 
                        onClick={handleLogout}
                        className="w-full flex items-center gap-3 px-3 py-2.5 text-sm font-bold text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 rounded-xl transition-colors"
                      >
                        <LogOut className="w-4 h-4" /> Sign Out
                      </button>
                    </motion.div>
                  </>
                )}
              </AnimatePresence>
            </div>
          </div>
        </header>

        {/* ── Page Content ── */}
        <main className="flex-1 overflow-x-hidden overflow-y-auto w-full relative z-0">
          <AnimatePresence mode="popLayout">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -15 }} transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
              className="h-full"
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}
