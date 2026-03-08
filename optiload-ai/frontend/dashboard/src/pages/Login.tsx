import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Truck, Eye, EyeOff, Loader2, User, Lock, Copy, CheckCircle2, Network, ArrowRight } from 'lucide-react';
import toast from 'react-hot-toast';
import { login } from '../api/client';

// Background Particles Component
function FloatingParticles() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {[...Array(20)].map((_, i) => (
        <motion.div
          key={i}
          className="absolute w-1 h-1 bg-white rounded-full opacity-20"
          initial={{
            x: Math.random() * window.innerWidth,
            y: Math.random() * window.innerHeight,
            scale: Math.random() * 0.5 + 0.5,
          }}
          animate={{
            y: [null, Math.random() * -200 - 50],
            opacity: [0, 0.4, 0],
          }}
          transition={{
            duration: Math.random() * 5 + 5,
            repeat: Infinity,
            ease: 'linear',
            delay: Math.random() * 5,
          }}
        />
      ))}
    </div>
  );
}

export default function LoginPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [isRedirecting, setIsRedirecting] = useState(false);

  // Focus states for micro-interactions
  const [userFocused, setUserFocused] = useState(false);
  const [passFocused, setPassFocused] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password) {
      toast.error('Please enter both username and password.');
      return;
    }
    setLoading(true);
    try {
      const res = await login(username, password);
      localStorage.setItem('access_token', res.data.access_token);
      toast.success(
        <div className="flex flex-col">
          <span className="font-bold">✔ Login Successful</span>
          <span className="text-xs opacity-80 mt-1">Redirecting to dashboard...</span>
        </div>,
        { duration: 2000, style: { background: '#10b981', color: '#fff', border: '1px solid #34d399' } }
      );
      
      setIsRedirecting(true);
      setTimeout(() => {
        navigate('/dashboard');
      }, 1200);
      
    } catch (err: any) {
      toast.error(
        <div className="flex flex-col">
          <span className="font-bold">Login Failed</span>
          <span className="text-xs opacity-80 mt-1">{err?.response?.data?.detail || 'Invalid credentials'}</span>
        </div>,
        { style: { background: '#f43f5e', color: '#fff', border: '1px solid #fb7185' } }
      );
    } finally {
      if (!isRedirecting) setLoading(false);
    }
  };

  const autofillDemo = () => {
    setUsername('admin');
    setPassword('demo123');
    setCopied(true);
    toast.success('Demo credentials injected!', { style: { background: '#6366f1', color: '#fff' } });
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <AnimatePresence>
      {!isRedirecting && (
        <motion.div 
          exit={{ opacity: 0, scale: 0.98, filter: 'blur(10px)' }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
          className="min-h-screen w-full flex bg-[#030712] font-sans selection:bg-indigo-500/30"
        >
          {/* ── Left Branding Panel (Hidden on Mobile) ── */}
          <div className="hidden lg:flex flex-col justify-between w-[45%] p-12 relative overflow-hidden bg-[#0a0f1e] border-r border-white/5">
            {/* Animated Background Gradients & Grid */}
            <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:40px_40px] pointer-events-none" />
            <motion.div 
              animate={{ rotate: 360, scale: [1, 1.1, 1] }} 
              transition={{ duration: 40, repeat: Infinity, ease: 'linear' }}
              className="absolute -bottom-48 -left-48 w-[600px] h-[600px] bg-fuchsia-600/10 blur-[120px] rounded-full pointer-events-none" 
            />
            <motion.div 
              animate={{ rotate: -360, scale: [1, 1.2, 1] }} 
              transition={{ duration: 50, repeat: Infinity, ease: 'linear' }}
              className="absolute top-1/4 -right-32 w-[500px] h-[500px] bg-indigo-600/10 blur-[120px] rounded-full pointer-events-none" 
            />

            <div className="relative z-10">
              <motion.div 
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}
                className="flex items-center gap-3 mb-16"
              >
                <motion.div 
                  animate={{ boxShadow: ['0 0 20px rgba(99,102,241,0.3)', '0 0 40px rgba(99,102,241,0.6)', '0 0 20px rgba(99,102,241,0.3)'] }}
                  transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
                  className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-cyan-500 flex items-center justify-center"
                >
                  <Truck className="w-5 h-5 text-white" />
                </motion.div>
                <span className="text-xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-white to-slate-400 tracking-tight">
                  OptiLoad AI
                </span>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.1 }}
                className="max-w-lg"
              >
                <h1 className="text-4xl xl:text-5xl font-black text-white leading-[1.15] tracking-tight mb-6">
                  Intelligent <br/>
                  <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-fuchsia-400">
                    Logistics OS
                  </span>
                </h1>
                <p className="text-slate-400 text-lg leading-relaxed font-medium">
                  Supercharge your supply chain with AI-powered cluster logic, real-time MILP multi-objective routing, and Monte Carlo resilience.
                </p>
              </motion.div>

              {/* Dashboard Preview Mockup */}
              <motion.div 
                initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, delay: 0.3 }}
                className="mt-12 p-6 rounded-2xl bg-white/[0.02] border border-white/5 backdrop-blur-md shadow-2xl relative overflow-hidden group"
              >
                <div className="absolute top-0 right-0 p-5 opacity-10 group-hover:opacity-20 transition-opacity duration-700">
                  <Network className="w-24 h-24 text-indigo-400" />
                </div>
                <div className="text-xs font-bold text-indigo-400 mb-5 tracking-wider uppercase flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" /> Live System Monitor
                </div>
                
                <div className="space-y-3">
                  {[
                    { label: 'Asset V-02 Activated (94% Fill)', dest: 'Mumbai → Pune' },
                    { label: 'Asset V-08 Activated (88% Fill)', dest: 'Delhi → Jaipur' },
                    { label: 'Cluster Assignment Generating...', dest: 'Bangalore Hub' }
                  ].map((m, i) => (
                    <motion.div 
                      key={i}
                      initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.6 + i*0.15 }}
                      whileHover={{ scale: 1.02, x: 5, backgroundColor: 'rgba(255,255,255,0.06)' }}
                      className="flex justify-between items-center bg-white/[0.03] p-3 rounded-xl border border-white/5 transition-all cursor-default"
                    >
                      <div className="flex items-center gap-3">
                        <div className={`p-1.5 rounded-md ${i === 2 ? 'bg-fuchsia-500/20 text-fuchsia-400 animate-pulse' : 'bg-emerald-500/20 text-emerald-400'}`}>
                          {i === 2 ? <Loader2 className="w-3 h-3 animate-spin" /> : <Truck className="w-3 h-3" />}
                        </div>
                        <span className="text-xs text-slate-300 font-medium">{m.label}</span>
                      </div>
                      <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">{m.dest}</span>
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            </div>

            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.8, delay: 0.6 }} className="relative z-10">
              <div className="flex items-center gap-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">
                <span>© 2026 OptiLoad Inc.</span>
                <span className="w-1 h-1 rounded-full bg-slate-800" />
                <a href="#" className="hover:text-slate-400 transition-colors">Privacy</a>
                <span className="w-1 h-1 rounded-full bg-slate-800" />
                <a href="#" className="hover:text-slate-400 transition-colors">Terms</a>
              </div>
            </motion.div>
          </div>

          {/* ── Right Auth Panel ── */}
          <div className="flex-1 flex flex-col items-center justify-center p-6 sm:p-12 relative w-full overflow-hidden">
            <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-indigo-900/10 via-[#030712] to-[#030712] pointer-events-none" />
            <FloatingParticles />
            
            {/* Mobile Logo */}
            <div className="lg:hidden flex items-center gap-3 mb-10 z-10">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-cyan-500 flex items-center justify-center shadow-[0_0_20px_rgba(99,102,241,0.3)]">
                <Truck className="w-6 h-6 text-white" />
              </div>
              <span className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-white to-slate-400 tracking-tight">
                OptiLoad AI
              </span>
            </div>

            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              whileHover={{ y: -4, boxShadow: '0 25px 50px -12px rgba(0,0,0,0.5)' }}
              transition={{ duration: 0.5, ease: "easeOut" }}
              className="w-full max-w-[440px] bg-[#0a0f1e]/80 backdrop-blur-2xl border border-white/5 rounded-[2rem] p-8 sm:p-10 shadow-2xl relative z-10 transition-shadow"
            >
              <div className="mb-8 text-center sm:text-left">
                <h2 className="text-2xl font-bold text-white tracking-tight mb-2">Welcome Back</h2>
                <p className="text-sm text-slate-400 font-medium">Log in to manage your optimization dashboard.</p>
              </div>

              <form onSubmit={handleLogin} className="space-y-5">
                {/* Username Input */}
                <div className="space-y-2">
                  <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Username</label>
                  <div className="relative group">
                    <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                      <User className={`w-4 h-4 transition-colors duration-300 ${userFocused ? 'text-indigo-400' : 'text-slate-500'}`} />
                    </div>
                    <input
                      type="text"
                      value={username}
                      onChange={e => setUsername(e.target.value)}
                      onFocus={() => setUserFocused(true)}
                      onBlur={() => setUserFocused(false)}
                      className="w-full bg-[#030712] border border-white/5 rounded-xl py-3.5 pl-11 pr-4 text-white text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all duration-300 placeholder-slate-600 shadow-inner hover:border-white/10"
                      placeholder="Enter username"
                      required
                    />
                  </div>
                </div>

                {/* Password Input */}
                <div className="space-y-2">
                  <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Password</label>
                  <div className="relative group">
                    <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                      <Lock className={`w-4 h-4 transition-colors duration-300 ${passFocused ? 'text-indigo-400' : 'text-slate-500'}`} />
                    </div>
                    <input
                      type={showPw ? 'text' : 'password'}
                      value={password}
                      onChange={e => setPassword(e.target.value)}
                      onFocus={() => setPassFocused(true)}
                      onBlur={() => setPassFocused(false)}
                      className="w-full bg-[#030712] border border-white/5 rounded-xl py-3.5 pl-11 pr-12 text-white text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all duration-300 placeholder-slate-600 shadow-inner hover:border-white/10"
                      placeholder="••••••••"
                      required
                    />
                    <button 
                      type="button" 
                      onClick={() => setShowPw(!showPw)}
                      className="absolute inset-y-0 right-0 pr-4 flex items-center text-slate-500 hover:text-white transition-colors outline-none"
                    >
                      <AnimatePresence mode="wait" initial={false}>
                        <motion.div
                          key={showPw ? 'hide' : 'show'}
                          initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.8 }}
                          transition={{ duration: 0.15 }}
                        >
                          {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </motion.div>
                      </AnimatePresence>
                    </button>
                  </div>
                </div>

                {/* Remember Me & Forgot Password */}
                <div className="flex items-center justify-between pt-1">
                  <label className="flex items-center gap-2 cursor-pointer group">
                    <div className={`w-4 h-4 rounded border transition-colors flex items-center justify-center ${rememberMe ? 'bg-indigo-500 border-indigo-500' : 'bg-[#030712] border-slate-600 group-hover:border-slate-400'}`}>
                      {rememberMe && <CheckCircle2 className="w-3 h-3 text-white" />}
                    </div>
                    <span className="text-xs font-medium text-slate-400 group-hover:text-slate-300 transition-colors">Remember me</span>
                    <input type="checkbox" className="hidden" checked={rememberMe} onChange={() => setRememberMe(!rememberMe)} />
                  </label>
                  <a href="#" className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition-colors">Forgot Password?</a>
                </div>

                {/* Submit Button */}
                <motion.button 
                  whileHover={{ scale: 1.01, y: -1 }}
                  whileTap={{ scale: 0.98 }}
                  type="submit" 
                  disabled={loading}
                  className="w-full py-3.5 bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white text-sm font-bold rounded-xl transition-all shadow-[0_4px_20px_rgba(99,102,241,0.3)] hover:shadow-[0_8px_25px_rgba(99,102,241,0.4)] flex items-center justify-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed mt-4"
                >
                  {loading ? (
                    <><Loader2 className="w-4 h-4 animate-spin" /> Signing in...</>
                  ) : (
                    'Sign In'
                  )}
                </motion.button>
              </form>

              {/* Enhanced Demo Credentials Card */}
              <div className="mt-8 pt-6 border-t border-white/5">
                <div className="bg-[#030712]/50 border border-white/5 rounded-xl p-5 flex flex-col gap-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded-md bg-indigo-500/20 flex items-center justify-center">
                        <Lock className="w-3 h-3 text-indigo-400" />
                      </div>
                      <span className="text-xs font-bold text-white tracking-wide">Demo Account</span>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-3 mb-1">
                    <div className="bg-white/5 p-2 rounded-lg border border-white/5 text-center">
                      <div className="text-[10px] text-slate-500 uppercase tracking-wider font-bold mb-1">Username</div>
                      <div className="text-xs text-slate-300 font-mono">admin</div>
                    </div>
                    <div className="bg-white/5 p-2 rounded-lg border border-white/5 text-center">
                      <div className="text-[10px] text-slate-500 uppercase tracking-wider font-bold mb-1">Password</div>
                      <div className="text-xs text-slate-300 font-mono">demo123</div>
                    </div>
                  </div>

                  <motion.button 
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.97 }}
                    onClick={autofillDemo}
                    className="w-full py-2.5 rounded-lg bg-white/5 hover:bg-white/10 text-xs font-bold text-indigo-300 flex items-center justify-center gap-2 transition-colors border border-white/5 hover:border-indigo-500/30 group"
                  >
                    {copied ? (
                      <><CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Credentials Copied</>
                    ) : (
                      <>Autofill Credentials <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" /></>
                    )}
                  </motion.button>
                </div>
              </div>

            </motion.div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
