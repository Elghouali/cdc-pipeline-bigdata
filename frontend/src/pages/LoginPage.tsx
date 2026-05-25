import { FormEvent, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { AlertCircle, Lock, WifiOff } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';

const PIPELINE_NODES = [
  { id: 'pg',      label: 'PostgreSQL', sublabel: ':5432', color: '#58A6FF', bg: '#58A6FF18' },
  { id: 'kafka',   label: 'Kafka',      sublabel: ':9092', color: '#FFA657', bg: '#FFA65718' },
  { id: 'spark',   label: 'Spark',      sublabel: ':7077', color: '#D29922', bg: '#D2992218' },
  { id: 'iceberg', label: 'Iceberg',    sublabel: 'tables', color: '#79C0FF', bg: '#79C0FF18' },
  { id: 'trino',   label: 'Trino',      sublabel: ':8080', color: '#BC8CFF', bg: '#BC8CFF18' },
  { id: 'minio',   label: 'MinIO',      sublabel: ':9000', color: '#3FB950', bg: '#3FB95018' },
];

const TECH_PILLS = ['KAFKA', 'SPARK', 'ICEBERG', 'TRINO', 'MINIO'];

function PipelineDiagram() {
  const nodeW = 80;
  const gap = 28;

  return (
    <div className="relative flex items-center">
      {PIPELINE_NODES.map((node, idx) => (
        <div key={node.id} className="flex items-center">
          {/* Node */}
          <div className="group relative flex flex-col items-center" style={{ width: nodeW }}>
            {/* Tooltip */}
            <div className="pointer-events-none absolute -top-9 left-1/2 z-10 -translate-x-1/2 whitespace-nowrap rounded border border-[--border] bg-[--bg-surface] px-2 py-1 font-mono text-[9px] text-[--text-muted] opacity-0 transition-opacity group-hover:opacity-100">
              {node.label} · {node.sublabel}
            </div>
            <div
              className="relative flex h-14 w-full flex-col items-center justify-center rounded-lg border transition-transform group-hover:scale-105"
              style={{ backgroundColor: node.bg, borderColor: `${node.color}45` }}
            >
              <span className="absolute -right-1 -top-1 h-2.5 w-2.5 rounded-full border-2 border-[--bg-base] node-glow" style={{ backgroundColor: '#3FB950' }} />
              <span className="font-mono text-[10px] font-bold" style={{ color: node.color }}>{node.label}</span>
              <span className="font-mono text-[8px] mt-0.5" style={{ color: `${node.color}80` }}>{node.sublabel}</span>
            </div>
          </div>

          {/* Arrow connector */}
          {idx < PIPELINE_NODES.length - 1 && (
            <div className="relative mx-1 flex items-center" style={{ width: gap }}>
              <div className="h-px w-full bg-[--border]" />
              <svg
                className="absolute left-0 w-full overflow-visible"
                height="3"
                viewBox={`0 0 ${gap} 3`}
                preserveAspectRatio="none"
              >
                <line
                  x1="0" y1="1.5" x2={gap} y2="1.5"
                  stroke={node.color}
                  strokeWidth="1.5"
                  strokeDasharray="5 5"
                  opacity="0.65"
                  className="dash-flow"
                  style={{ animationDelay: `${idx * 0.35}s` }}
                />
              </svg>
              <svg className="absolute right-0 shrink-0" width="6" height="7" viewBox="0 0 6 7">
                <path d="M0 0 L6 3.5 L0 7 Z" fill={node.color} opacity="0.55" />
              </svg>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function getErrorType(msg: string): 'server' | 'auth' | 'network' | 'generic' {
  if (msg.includes('500') || msg.includes('API')) return 'server';
  if (msg.includes('401') || msg.includes('credentials') || msg.includes('Invalid')) return 'auth';
  if (msg.includes('fetch') || msg.includes('network') || msg.includes('Failed to fetch')) return 'network';
  return 'generic';
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

  const errType = error ? getErrorType(error) : null;

  return (
    <div className="flex min-h-screen bg-[--bg-base]">

      {/* LEFT panel (60%) */}
      <div
        className="relative hidden flex-col items-center justify-center overflow-hidden lg:flex"
        style={{ width: '60%' }}
      >
        <div className="dot-grid absolute inset-0 opacity-50" />
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_70%_60%_at_50%_50%,transparent_30%,#0D1117_100%)]" />

        <div className="relative z-10 flex flex-col items-center gap-12 px-16">
          <div className="text-center">
            <p className="mb-3 font-mono text-[10px] uppercase tracking-[0.25em] text-[--text-dim]">
              Real-time data engineering control center
            </p>
            <h1 className="text-4xl font-bold tracking-tight text-[--text-primary]">
              Medallion <span className="gradient-text">Pipeline</span>
            </h1>
            <p className="mt-2 text-sm text-[--text-muted]">
              End-to-end CDC · Bronze → Silver → Gold
            </p>
          </div>

          <div className="overflow-x-auto pb-2">
            <PipelineDiagram />
          </div>

          <div className="flex items-center gap-3">
            {[
              { label: 'BRONZE', color: '#B08050' },
              { label: 'SILVER', color: '#8B949E' },
              { label: 'GOLD',   color: '#D29922' },
            ].map(({ label, color }) => (
              <span
                key={label}
                className="rounded border px-2.5 py-1 font-mono text-[10px] font-semibold tracking-[0.1em]"
                style={{ borderColor: `${color}40`, color, backgroundColor: `${color}10` }}
              >
                {label}
              </span>
            ))}
            <span className="font-mono text-[10px] text-[--text-dim]">v1.0</span>
          </div>
        </div>
      </div>

      {/* RIGHT panel (40%) */}
      <div className="flex flex-1 flex-col items-center justify-center border-l border-[--border] bg-[--bg-surface] px-8 py-12 lg:px-12">
        <div className="w-full" style={{ maxWidth: 380 }}>

          <div className="mb-8">
            <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-lg border border-[--border] bg-[--bg-elevated]">
              <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="#00D4FF" strokeWidth={2}>
                <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-[--text-primary]">CDC Pipeline</h2>
            <p className="mt-1 font-mono text-[10px] uppercase tracking-[0.15em] text-[--text-dim]">
              MEDALLION REAL-TIME CONSOLE
            </p>
          </div>

          {error && (
            <div className={`mb-5 flex items-start gap-3 rounded-lg border p-3 ${
              errType === 'auth'    ? 'border-[#F85149]/30 bg-[#F85149]/8' :
              errType === 'network' ? 'border-[--border] bg-[--bg-elevated]' :
              errType === 'server'  ? 'border-[#D29922]/30 bg-[#D29922]/8' :
                                     'border-[--border] bg-[--bg-elevated]'
            }`}>
              {errType === 'auth'    && <Lock    className="mt-0.5 h-4 w-4 shrink-0 text-[#F85149]" />}
              {errType === 'network' && <WifiOff  className="mt-0.5 h-4 w-4 shrink-0 text-[--text-muted]" />}
              {(errType === 'server' || errType === 'generic') && <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-[#D29922]" />}
              <p className="text-sm" style={{
                color: errType === 'auth' ? '#F85149' : errType === 'server' ? '#D29922' : '#8B949E',
              }}>
                {errType === 'network' ? 'Cannot reach server — check your connection' :
                 errType === 'auth'    ? 'Invalid credentials' :
                 errType === 'server'  ? 'API unreachable on :8000' :
                 error}
              </p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="username" className="mb-1.5 block text-[11px] font-semibold uppercase tracking-[0.08em] text-[--text-muted]">
                Username
              </label>
              <input
                id="username"
                type="text"
                autoComplete="username"
                required
                value={username}
                onChange={e => setUsername(e.target.value)}
                placeholder="admin"
                className="h-12 w-full rounded-md border border-[--border] bg-[--bg-elevated] px-3.5 text-sm text-[--text-primary] placeholder-[--text-dim] outline-none transition-all focus:border-[--accent-cyan] focus:ring-2 focus:ring-[--accent-cyan]/20"
              />
            </div>
            <div>
              <label htmlFor="password" className="mb-1.5 block text-[11px] font-semibold uppercase tracking-[0.08em] text-[--text-muted]">
                Password
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                className="h-12 w-full rounded-md border border-[--border] bg-[--bg-elevated] px-3.5 text-sm text-[--text-primary] placeholder-[--text-dim] outline-none transition-all focus:border-[--accent-cyan] focus:ring-2 focus:ring-[--accent-cyan]/20"
              />
            </div>
            <button
              type="submit"
              disabled={loading || !username.trim() || !password.trim()}
              className="mt-6 h-12 w-full rounded-md text-sm font-semibold text-white transition-all active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed"
              style={{ background: 'linear-gradient(135deg, #00D4FF 0%, #BC8CFF 100%)' }}
            >
              {loading ? 'Signing in…' : 'Sign in →'}
            </button>
          </form>

          <div className="mt-8 flex flex-wrap gap-1.5">
            {TECH_PILLS.map(t => (
              <span key={t} className="rounded border border-[--border] bg-[--bg-elevated] px-2 py-0.5 font-mono text-[9px] uppercase tracking-[0.1em] text-[--text-dim]">
                {t}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
