import { FormEvent, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { Zap } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/Button';

const TECH_STACK = ['Kafka', 'Spark', 'Iceberg', 'Trino', 'MinIO'];

export function LoginPage() {
  const { isAuthenticated, login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  if (isAuthenticated) {
    return <Navigate to="/health" replace />;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(username, password);
      navigate('/health', { replace: true });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-[--bg-base] px-4">
      {/* Animated blobs */}
      <div aria-hidden className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="blob-animate absolute -left-40 -top-40 h-[480px] w-[480px] rounded-full bg-cyan-500/[0.08] blur-[120px]" />
        <div className="blob-animate-delay absolute left-1/2 top-1/2 h-[640px] w-[640px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-purple-500/[0.07] blur-[140px]" />
        <div className="blob-animate-slow absolute -bottom-40 -right-40 h-[420px] w-[420px] rounded-full bg-emerald-500/[0.06] blur-[120px]" />
      </div>

      {/* Mesh grid */}
      <div aria-hidden className="mesh-grid pointer-events-none fixed inset-0 opacity-40" />

      {/* Vignette */}
      <div aria-hidden className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_at_center,transparent_25%,var(--bg-base)_85%)]" />

      <div className="relative z-10 w-full max-w-md">
        {/* Brand hero */}
        <div className="mb-10 flex flex-col items-center gap-5">
          <div className="relative flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-500/30 via-purple-500/20 to-purple-600/30 ring-1 ring-white/10 shadow-[0_0_48px_rgba(0,229,255,0.25)]">
            <Zap className="h-8 w-8 text-cyan-200" strokeWidth={2.25} />
            <span className="absolute -inset-2 -z-10 rounded-3xl bg-gradient-to-br from-cyan-500/20 to-purple-600/20 blur-xl" />
            <span aria-hidden className="absolute -top-px left-1/2 h-px w-24 -translate-x-1/2 bg-gradient-to-r from-transparent via-cyan-300 to-transparent" />
          </div>
          <div className="text-center">
            <h1 className="gradient-text text-3xl font-black tracking-tight">CDC Pipeline</h1>
            <p className="mt-2 text-xs font-medium uppercase tracking-[0.3em] text-[--text-muted]">
              Medallion · Real-time Console
            </p>
          </div>
        </div>

        {/* Form card — glass */}
        <form
          onSubmit={handleSubmit}
          className="relative space-y-5 overflow-hidden rounded-2xl border border-white/[0.06] bg-[--bg-glass] p-7 backdrop-blur-xl shadow-[0_24px_64px_rgba(0,0,0,0.55),inset_0_1px_0_rgba(255,255,255,0.05)]"
        >
          <div aria-hidden className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cyan-400/80 to-transparent" />

          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-[--text-muted]">Welcome back</p>
            <p className="mt-1 text-lg font-semibold text-[--text-primary]">Sign in to your workspace</p>
          </div>

          {error && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
              {error}
            </div>
          )}

          <div className="space-y-1.5">
            <label htmlFor="username" className="text-[11px] font-semibold uppercase tracking-wider text-[--text-secondary]">
              Username
            </label>
            <input
              id="username"
              type="text"
              autoComplete="username"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full rounded-lg border border-white/[0.06] bg-white/[0.02] px-3.5 py-2.5 text-sm text-[--text-primary] placeholder-[--text-muted] outline-none transition-all focus:border-cyan-400/50 focus:bg-white/[0.04] focus:ring-2 focus:ring-cyan-500/20"
              placeholder="admin"
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="password" className="text-[11px] font-semibold uppercase tracking-wider text-[--text-secondary]">
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-white/[0.06] bg-white/[0.02] px-3.5 py-2.5 text-sm text-[--text-primary] placeholder-[--text-muted] outline-none transition-all focus:border-cyan-400/50 focus:bg-white/[0.04] focus:ring-2 focus:ring-cyan-500/20"
              placeholder="••••••••"
            />
          </div>

          <Button type="submit" size="lg" isLoading={loading} className="w-full">
            {loading ? 'Signing in…' : 'Sign in →'}
          </Button>
        </form>

        {/* Tech stack chips */}
        <div className="mt-7 flex flex-wrap items-center justify-center gap-1.5">
          {TECH_STACK.map((t, i) => (
            <span
              key={t}
              className="rounded-full border border-white/[0.06] bg-white/[0.02] px-2.5 py-1 font-mono text-[10px] font-medium uppercase tracking-wider text-[--text-secondary] backdrop-blur"
            >
              {t}
              {i < TECH_STACK.length - 1 && <span className="ml-1.5 text-[--text-muted]/50">·</span>}
            </span>
          ))}
        </div>

        <p className="mt-5 text-center font-mono text-[10px] uppercase tracking-widest text-[--text-muted]">
          v1.0 · Bronze · Silver · Gold
        </p>
      </div>
    </div>
  );
}
