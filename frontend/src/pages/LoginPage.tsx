import { FormEvent, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { Lock, Database, Share2, Zap, Layers, Server, HardDrive } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';

const PIPELINE_NODES = [
  { id: 'pg',      label: 'PostgreSQL', sublabel: ':5432', color: '#58A6FF', icon: Database },
  { id: 'kafka',   label: 'Kafka',      sublabel: ':9092', color: '#FFA657', icon: Share2 },
  { id: 'spark',   label: 'Spark',      sublabel: ':7077', color: '#D29922', icon: Zap },
  { id: 'iceberg', label: 'Iceberg',    sublabel: 'tables', color: '#79C0FF', icon: Layers },
  { id: 'trino',   label: 'Trino',      sublabel: ':8080', color: '#BC8CFF', icon: Server },
  { id: 'minio',   label: 'MinIO',      sublabel: ':9000', color: '#3FB950', icon: HardDrive },
];

function PipelineDiagram() {
  return (
    <div className="relative flex items-center justify-center w-full max-w-4xl px-8 mt-12">
      {PIPELINE_NODES.map((node, idx) => {
        const Icon = node.icon;
        return (
          <div key={node.id} className="flex items-center">
            {/* Node */}
            <div className="group relative flex flex-col items-center w-20">
              {/* Tooltip */}
              <div className="pointer-events-none absolute -top-12 left-1/2 z-20 -translate-x-1/2 whitespace-nowrap rounded-lg border border-white/10 bg-black/60 px-4 py-2 font-mono text-xs text-white opacity-0 shadow-2xl backdrop-blur-md transition-all duration-300 group-hover:-top-14 group-hover:opacity-100">
                <span className="font-bold tracking-wide" style={{ color: node.color }}>{node.label}</span>
                <span className="ml-2 text-white/50">{node.sublabel}</span>
              </div>
              
              <div
                className="relative flex h-20 w-20 items-center justify-center rounded-2xl border border-white/10 bg-white/5 backdrop-blur-lg transition-all duration-500 group-hover:-translate-y-2 group-hover:scale-110"
                style={{ boxShadow: `0 8px 32px ${node.color}15, inset 0 1px 1px rgba(255,255,255,0.2)` }}
              >
                {/* Glow Behind Icon */}
                <div className="absolute inset-0 rounded-2xl opacity-0 transition-opacity duration-500 group-hover:opacity-100" style={{ background: `radial-gradient(circle at center, ${node.color}40 0%, transparent 70%)` }} />
                
                {/* Live Status Dot */}
                <span className="absolute -right-1.5 -top-1.5 flex h-4 w-4 items-center justify-center">
                  <span className="absolute inline-flex h-full w-full rounded-full bg-[#00ffaa] opacity-75 status-pulse" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-[#00ffaa] shadow-[0_0_10px_#00ffaa]" />
                </span>
                
                <Icon className="relative z-10 h-8 w-8 transition-colors duration-300" style={{ color: node.color }} strokeWidth={1.5} />
              </div>
            </div>

            {/* Connection Arrow */}
            {idx < PIPELINE_NODES.length - 1 && (
              <div className="relative mx-8 flex w-16 items-center">
                <svg className="w-full h-2 overflow-visible" preserveAspectRatio="none">
                  <line
                    x1="0" y1="4" x2="100%" y2="4"
                    stroke={node.color}
                    strokeWidth="1.5"
                    strokeDasharray="4 4"
                    className="dash-flow-fast"
                    opacity="0.4"
                  />
                  <polygon points="60,1 66,4 60,7" fill={node.color} opacity="0.6" />
                </svg>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export function LoginPage() {
  const { isAuthenticated, login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  if (isAuthenticated) return <Navigate to="/dashboard" replace />;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(username, password);
      navigate('/dashboard', { replace: true });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen bg-black font-sans selection:bg-cyan-500/30 selection:text-white">

      {/* LEFT panel (60%) */}
      <div className="relative hidden w-[60%] flex-col items-center justify-center overflow-hidden border-r border-white/5 lg:flex">
        {/* Antigravity Orbs */}
        <div className="absolute left-[-10%] top-[-10%] h-[600px] w-[600px] rounded-full bg-[#BC8CFF] opacity-10 blur-[100px] mix-blend-screen" />
        <div className="absolute bottom-[-10%] right-[-10%] h-[600px] w-[600px] rounded-full bg-[#00D4FF] opacity-10 blur-[100px] mix-blend-screen" />
        
        {/* Fine SVG Grid */}
        <div className="absolute inset-0 z-0 opacity-20" style={{ backgroundImage: 'url("data:image/svg+xml,%3Csvg width=\'32\' height=\'32\' viewBox=\'0 0 32 32\' fill=\'none\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Ccircle cx=\'1\' cy=\'1\' r=\'1\' fill=\'rgba(255,255,255,0.5)\'/%3E%3C/svg%3E")' }} />
        
        {/* Radial Fade */}
        <div className="pointer-events-none absolute inset-0 z-0 bg-[radial-gradient(circle_at_center,transparent_0%,#000000_85%)]" />

        <div className="relative z-10 flex w-full flex-col items-center justify-center">
          <PipelineDiagram />
        </div>

        {/* Floating Glass Badge */}
        <div className="absolute bottom-12 z-10 flex items-center gap-6 rounded-full border border-white/10 bg-white/[0.03] px-8 py-3.5 shadow-[0_8px_32px_rgba(0,0,0,0.4)] backdrop-blur-xl">
          <span className="font-mono text-[12px] font-bold text-white/60">v1.0.4</span>
          <div className="h-4 w-px bg-white/10" />
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-2 font-mono text-[11px] font-bold tracking-widest text-[#FFA657] drop-shadow-[0_0_8px_rgba(255,166,87,0.4)]">
              <div className="h-1.5 w-1.5 rounded-full bg-[#FFA657]" /> BRONZE
            </span>
            <span className="font-mono text-[11px] font-bold tracking-widest text-white/20">/</span>
            <span className="flex items-center gap-2 font-mono text-[11px] font-bold tracking-widest text-[#E6EDF3] drop-shadow-[0_0_8px_rgba(230,237,243,0.4)]">
              <div className="h-1.5 w-1.5 rounded-full bg-[#E6EDF3]" /> SILVER
            </span>
            <span className="font-mono text-[11px] font-bold tracking-widest text-white/20">/</span>
            <span className="flex items-center gap-2 font-mono text-[11px] font-bold tracking-widest text-[#D29922] drop-shadow-[0_0_8px_rgba(210,153,34,0.4)]">
              <div className="h-1.5 w-1.5 rounded-full bg-[#D29922]" /> GOLD
            </span>
          </div>
        </div>
      </div>

      {/* RIGHT panel (40%) */}
      <div className="relative flex w-full flex-col items-center justify-center bg-[#050505] p-16 lg:w-[40%] shadow-[-20px_0_40px_rgba(0,0,0,0.5)] z-20">
        
        {/* Ambient subtle glow on the right panel */}
        <div className="pointer-events-none absolute left-1/2 top-1/2 h-[500px] w-[500px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#BC8CFF] opacity-[0.04] blur-[100px]" />

        <div className="relative z-10 w-full max-w-[420px]">
          
          {/* Header */}
          <div className="mb-16 flex flex-col items-center text-center">
            <div className="relative mb-8 flex h-16 w-16 items-center justify-center rounded-2xl bg-[#0A0A0A] border border-white/10 shadow-[0_8px_16px_rgba(0,0,0,0.4)]">
              <div className="absolute inset-0 rounded-2xl bg-gradient-to-tr from-[#00D4FF]/10 to-[#BC8CFF]/10" />
              <Zap className="h-6 w-6 text-white drop-shadow-[0_0_10px_rgba(255,255,255,0.5)]" strokeWidth={2} />
            </div>
            <h1 className="text-[26px] font-semibold tracking-tight text-white drop-shadow-sm">Sign in to Console</h1>
            <p className="mt-2 text-[14px] text-white/40">
              Enter your credentials to access the pipeline.
            </p>
          </div>

          {/* Error Banner */}
          {error && (
            <div className="mb-6 flex items-center gap-3 rounded-xl border border-red-500/30 bg-red-500/10 p-4 shadow-[0_0_20px_rgba(248,81,73,0.1)] backdrop-blur-md">
              <Lock className="h-5 w-5 shrink-0 text-red-400" />
              <p className="text-sm font-medium text-red-200">
                {error.includes('fetch') ? 'Cannot reach server' : 'Invalid credentials'}
              </p>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-8">
            <div className="space-y-2.5">
              <label className="block px-1 text-[13px] font-medium text-white/70">
                Username or Service Account
              </label>
              <input
                type="text"
                required
                value={username}
                onChange={e => setUsername(e.target.value)}
                placeholder="e.g. data_eng_admin"
                className="h-[52px] w-full rounded-xl border border-white/10 bg-[#0A0A0A] px-4 text-[15px] text-white shadow-sm outline-none transition-all duration-200 placeholder:text-white/20 hover:border-white/20 focus:border-[#00D4FF]/60 focus:bg-white/[0.02] focus:shadow-[0_0_0_4px_rgba(0,212,255,0.1)]"
              />
            </div>
            <div className="space-y-2">
              <label className="flex items-center justify-between px-1 text-[13px] font-medium text-white/70">
                <span>Password</span>
                <span className="text-[11px] text-[#00D4FF]/70 hover:text-[#00D4FF] cursor-pointer">Forgot?</span>
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="h-[52px] w-full rounded-xl border border-white/10 bg-[#0A0A0A] px-4 text-[15px] text-white tracking-widest shadow-sm outline-none transition-all duration-200 placeholder:text-white/20 placeholder:tracking-normal hover:border-white/20 focus:border-[#00D4FF]/60 focus:bg-white/[0.02] focus:shadow-[0_0_0_4px_rgba(0,212,255,0.1)]"
              />
            </div>
            
            <button
              type="submit"
              disabled={loading}
              className="group relative mt-10 flex h-[52px] w-full items-center justify-center overflow-hidden rounded-xl bg-white text-[15px] font-semibold text-black transition-all duration-300 hover:scale-[1.02] active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50"
            >
              {/* Subtle hover gradient inside the white button */}
              <div className="absolute inset-0 bg-gradient-to-r from-cyan-100 to-purple-100 opacity-0 transition-opacity duration-300 group-hover:opacity-100 mix-blend-multiply" />
              <span className="relative z-10 flex items-center gap-2">
                {loading ? 'Authenticating...' : 'Continue'}
                {!loading && <span className="transition-transform duration-300 group-hover:translate-x-1">→</span>}
              </span>
            </button>
          </form>

          {/* Footer Pills */}
          <div className="mt-16 border-t border-white/5 pt-10">
            <p className="mb-6 text-center text-[11px] font-medium uppercase tracking-[0.2em] text-white/30">
              Core Infrastructure
            </p>
            <div className="flex flex-wrap items-center justify-center gap-4">
              {['Kafka', 'Spark', 'Iceberg', 'Trino', 'MinIO'].map(tech => (
                <span key={tech} className="flex items-center gap-2 rounded-full border border-white/5 bg-white/[0.02] px-4 py-2 text-[11px] font-medium text-white/50 transition-colors hover:border-white/20 hover:text-white/90">
                  <span className="h-1.5 w-1.5 rounded-full bg-white/20" />
                  {tech}
                </span>
              ))}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
