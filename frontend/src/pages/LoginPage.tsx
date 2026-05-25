import { FormEvent, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { Zap } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/Button';

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
    <div className="flex min-h-screen flex-col items-center justify-center bg-[--bg-base] px-4">
      {/* Animated background blobs */}
      <div aria-hidden className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="blob-animate absolute -left-40 -top-40 h-96 w-96 rounded-full bg-cyan-500/8 blur-3xl" />
        <div className="blob-animate-delay absolute left-1/2 top-1/2 h-[520px] w-[520px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-purple-500/5 blur-3xl" />
        <div className="blob-animate-slow absolute -bottom-40 -right-40 h-80 w-80 rounded-full bg-emerald-500/6 blur-3xl" />
      </div>

      {/* Vignette over the dot grid */}
      <div aria-hidden className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_at_center,transparent_30%,var(--bg-base)_80%)]" />

      <div className="relative z-10 w-full max-w-sm">
        {/* Brand */}
        <div className="mb-8 flex flex-col items-center gap-3">
          <div className="relative flex h-14 w-14 items-center justify-center rounded-2xl border border-cyan-500/30 bg-cyan-500/10 shadow-[0_0_32px_rgba(0,212,255,0.12)]">
            <Zap className="h-7 w-7 text-cyan-400" />
            <span className="absolute -top-px left-1/2 h-px w-16 -translate-x-1/2 bg-gradient-to-r from-transparent via-cyan-400/60 to-transparent" />
          </div>
          <div className="text-center">
            <h1 className="text-xl font-bold text-[--text-primary]">CDC Pipeline Console</h1>
            <p className="mt-1 text-sm text-[--text-muted]">Sign in to your workspace</p>
          </div>
        </div>

        {/* Form card */}
        <form
          onSubmit={handleSubmit}
          className="space-y-4 rounded-xl border border-[--border-focus] bg-[--bg-surface] p-6 shadow-[0_0_0_1px_rgba(30,42,61,0.5),0_24px_48px_rgba(0,0,0,0.4)]"
        >
          {error && (
            <div className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-400">
              {error}
            </div>
          )}

          <div className="space-y-1.5">
            <label htmlFor="username" className="text-xs font-medium text-[--text-secondary]">
              Username
            </label>
            <input
              id="username"
              type="text"
              autoComplete="username"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full rounded-md border border-[--border] bg-[--bg-elevated] px-3 py-2 text-sm text-[--text-primary] placeholder-[--text-muted] outline-none transition-colors focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/30"
              placeholder="admin"
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="password" className="text-xs font-medium text-[--text-secondary]">
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-md border border-[--border] bg-[--bg-elevated] px-3 py-2 text-sm text-[--text-primary] placeholder-[--text-muted] outline-none transition-colors focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/30"
              placeholder="••••••••"
            />
          </div>

          <Button type="submit" size="lg" isLoading={loading} className="w-full">
            {loading ? 'Signing in…' : 'Sign in'}
          </Button>
        </form>

        <p className="mt-5 text-center text-xs text-[--text-muted]">
          Medallion Architecture · CDC Pipeline v1.0
        </p>
      </div>
    </div>
  );
}
