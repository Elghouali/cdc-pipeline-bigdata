import { FormEvent, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { AlertCircle, Database, HardDrive, Layers, Server, Share2, Workflow, Zap } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';

const PIPELINE_NODES = [
  { id: 'pg',      label: 'PostgreSQL', sublabel: ':5432',  color: '#2563EB', icon: Database },
  { id: 'kafka',   label: 'Kafka',      sublabel: ':9092',  color: '#EA580C', icon: Share2  },
  { id: 'spark',   label: 'Spark',      sublabel: ':7077',  color: '#CA8A04', icon: Zap     },
  { id: 'iceberg', label: 'Iceberg',    sublabel: 'tables', color: '#7C3AED', icon: Layers  },
  { id: 'trino',   label: 'Trino',      sublabel: ':8080',  color: '#7C3AED', icon: Server  },
  { id: 'minio',   label: 'MinIO',      sublabel: ':9000',  color: '#16A34A', icon: HardDrive },
];

function PipelineDiagram() {
  return (
    <div className="w-full max-w-lg">
      <div className="flex items-center justify-between gap-2">
        {PIPELINE_NODES.map((node, idx) => {
          const Icon = node.icon;
          return (
            <div key={node.id} className="flex items-center gap-2">
              <div className="group flex flex-col items-center gap-2">
                <div
                  className="flex h-12 w-12 items-center justify-center rounded-xl border transition-all duration-300 group-hover:-translate-y-1 group-hover:shadow-md"
                  style={{
                    backgroundColor: `${node.color}0F`,
                    borderColor: `${node.color}28`,
                  }}
                >
                  <Icon className="h-5 w-5" style={{ color: node.color }} strokeWidth={1.75} />
                </div>
                <div className="text-center">
                  <p className="text-[10px] font-semibold text-[--text-secondary]">{node.label}</p>
                  <p className="font-mono text-[9px] text-[--text-dim]">{node.sublabel}</p>
                </div>
              </div>
              {idx < PIPELINE_NODES.length - 1 && (
                <div className="mb-6 flex w-6 items-center">
                  <svg className="w-full overflow-visible" height="8" preserveAspectRatio="none">
                    <line
                      x1="0" y1="4" x2="100%" y2="4"
                      stroke={node.color}
                      strokeWidth="1.5"
                      strokeDasharray="3 3"
                      className="dash-flow-fast"
                      opacity="0.4"
                    />
                    <polygon points="18,2 22,4 18,6" fill={node.color} opacity="0.5" />
                  </svg>
                </div>
              )}
            </div>
          );
        })}
      </div>
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
    <div className="flex min-h-screen bg-[--bg-base] font-sans">

      {/* LEFT: illustration panel */}
      <div className="relative hidden w-[55%] flex-col items-center justify-center overflow-hidden bg-[--bg-elevated] border-r border-[--border] lg:flex">
        {/* Subtle dot grid */}
        <div className="absolute inset-0 dot-grid opacity-60" />

        {/* Soft radial gradient */}
        <div className="pointer-events-none absolute inset-0" style={{
          background: 'radial-gradient(ellipse 60% 60% at 50% 50%, rgba(207,108,79,0.06) 0%, transparent 70%)'
        }} />

        <div className="relative z-10 flex flex-col items-center gap-16 px-12">
          {/* Headline */}
          <div className="text-center">
            <div className="mb-5 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-[--accent] shadow-md">
              <Workflow className="h-6 w-6 text-white" strokeWidth={2} />
            </div>
            <h2 className="text-2xl font-semibold text-[--text-primary]">CDC Pipeline</h2>
            <p className="mt-2 text-sm text-[--text-muted]">Real-time medallion data infrastructure</p>
          </div>

          {/* Pipeline diagram */}
          <PipelineDiagram />

          {/* Layer badges */}
          <div className="flex items-center gap-3">
            {[
              { label: 'Bronze', color: '#F59E0B', bg: 'rgba(245,158,11,0.1)' },
              { label: 'Silver', color: '#9CA3AF', bg: 'rgba(156,163,175,0.08)' },
              { label: 'Gold',   color: '#FCD34D', bg: 'rgba(252,211,77,0.1)' },
            ].map(layer => (
              <span
                key={layer.label}
                className="flex items-center gap-2 rounded-full border px-4 py-1.5 text-[11px] font-semibold tracking-wide"
                style={{ backgroundColor: layer.bg, borderColor: `${layer.color}30`, color: layer.color }}
              >
                <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: layer.color }} />
                {layer.label.toUpperCase()}
              </span>
            ))}
          </div>
        </div>

        {/* Version badge */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2">
          <span className="font-mono text-[11px] text-[--text-dim]">v1.0.4 · Medallion Architecture</span>
        </div>
      </div>

      {/* RIGHT: login form */}
      <div className="flex w-full flex-col items-center justify-center bg-[--bg-surface] p-12 lg:w-[45%]">
        <div className="w-full max-w-[380px]">

          {/* Header */}
          <div className="mb-10">
            <div className="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-xl bg-[--accent-subtle] lg:hidden">
              <Workflow className="h-5 w-5 text-[--accent]" strokeWidth={2} />
            </div>
            <h1 className="text-[22px] font-semibold text-[--text-primary]">Sign in to Console</h1>
            <p className="mt-1.5 text-[13px] text-[--text-muted]">
              Enter your credentials to access the pipeline.
            </p>
          </div>

          {/* Error Banner */}
          {error && (
            <div className="mb-6 flex items-start gap-3 rounded-xl border border-[--accent-red]/20 bg-[--accent-red]/10 p-4">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-[--accent-red]" />
              <p className="text-[13px] text-[--accent-red]">
                {error.includes('fetch') ? 'Cannot reach server. Check your connection.' : 'Invalid username or password.'}
              </p>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="mb-1.5 block text-[13px] font-medium text-[--text-secondary]">
                Username
              </label>
              <input
                type="text"
                required
                value={username}
                onChange={e => setUsername(e.target.value)}
                placeholder="e.g. data_eng_admin"
                className="h-11 w-full rounded-lg border border-[--border] bg-[--bg-base] px-4 text-[14px] text-[--text-primary] outline-none transition-all placeholder:text-[--text-dim] hover:border-[--text-dim] focus:border-[--accent] focus:ring-3 focus:ring-[--accent-subtle]"
              />
            </div>

            <div>
              <div className="mb-1.5 flex items-center justify-between">
                <label className="text-[13px] font-medium text-[--text-secondary]">Password</label>
              </div>
              <input
                type="password"
                required
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••••"
                className="h-11 w-full rounded-lg border border-[--border] bg-[--bg-base] px-4 text-[14px] text-[--text-primary] tracking-widest outline-none transition-all placeholder:text-[--text-dim] placeholder:tracking-normal hover:border-[--text-dim] focus:border-[--accent] focus:ring-3 focus:ring-[--accent-subtle]"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="mt-2 flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-[--accent] text-[14px] font-semibold text-white transition-all hover:bg-[--accent-hover] active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                  <span>Authenticating…</span>
                </>
              ) : (
                'Continue'
              )}
            </button>
          </form>

          {/* Footer */}
          <div className="mt-10 border-t border-[--border] pt-8">
            <p className="mb-4 text-center text-[11px] font-medium uppercase tracking-widest text-[--text-dim]">
              Core Infrastructure
            </p>
            <div className="flex flex-wrap items-center justify-center gap-2">
              {['Kafka', 'Spark', 'Iceberg', 'Trino', 'MinIO'].map(tech => (
                <span
                  key={tech}
                  className="rounded-full border border-[--border] bg-[--bg-elevated] px-3 py-1 text-[11px] font-medium text-[--text-muted] transition-colors hover:border-[--accent]/30 hover:text-[--text-secondary]"
                >
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
