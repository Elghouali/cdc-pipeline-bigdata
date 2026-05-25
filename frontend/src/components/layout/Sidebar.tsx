import { NavLink } from 'react-router-dom';
import { Activity, Database, LayoutDashboard, LogOut, Workflow, Zap } from 'lucide-react';
import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/context/AuthContext';
import { fetchHealth } from '@/lib/api';

interface NavItem {
  to: string;
  icon: React.ElementType;
  label: string;
  iconBg: string;
  iconColor: string;
}

const NAV_ITEMS: NavItem[] = [
  { to: '/health',    icon: Activity,        label: 'Pipeline Health', iconBg: 'bg-emerald-500/15', iconColor: 'text-emerald-400' },
  { to: '/metrics',   icon: Database,        label: 'Data Layers',     iconBg: 'bg-cyan-500/15',    iconColor: 'text-cyan-400'    },
  { to: '/dashboard', icon: LayoutDashboard, label: 'KPI Dashboard',   iconBg: 'bg-purple-500/15',  iconColor: 'text-purple-400'  },
  { to: '/stats',     icon: Workflow,        label: 'Overview',        iconBg: 'bg-amber-500/15',   iconColor: 'text-amber-400'   },
];

export function Sidebar() {
  const { username, logout } = useAuth();
  const [status, setStatus] = useState<{ up: number; total: number } | null>(null);
  const [time, setTime] = useState(() => new Date());

  useEffect(() => {
    async function poll() {
      try {
        const items = await fetchHealth();
        setStatus({ up: items.filter(i => i.status === 'up').length, total: items.length });
      } catch { /* silent */ }
    }
    void poll();
    const id = setInterval(poll, 30_000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const id = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const allUp = status !== null && status.up === status.total;

  return (
    <aside className="relative flex h-screen w-60 shrink-0 flex-col border-r border-white/[0.04] bg-[--bg-surface]/80 backdrop-blur-xl">
      {/* subtle vertical gradient accent */}
      <div aria-hidden className="pointer-events-none absolute inset-y-0 left-0 w-px bg-gradient-to-b from-transparent via-cyan-500/20 to-transparent" />

      {/* Brand */}
      <div className="flex items-center gap-3 border-b border-white/[0.04] px-5 py-5">
        <div className="relative flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500/30 to-purple-600/30 ring-1 ring-white/10">
          <Zap className="h-4.5 w-4.5 text-cyan-300" strokeWidth={2.5} />
          <span className="absolute -inset-1 -z-10 rounded-2xl bg-gradient-to-br from-cyan-500/20 to-purple-600/20 blur-md" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="gradient-text text-sm font-bold tracking-tight">CDC Pipeline</p>
          <p className="text-[10px] font-medium uppercase tracking-widest text-[--text-muted]">Medallion Console</p>
        </div>
      </div>

      {/* Health pill */}
      {status && (
        <div className="px-4 pt-4">
          <div
            className={cn(
              'flex items-center justify-between rounded-lg border px-3 py-2',
              allUp
                ? 'border-emerald-500/20 bg-emerald-500/[0.04]'
                : 'border-amber-500/20 bg-amber-500/[0.04]',
            )}
          >
            <span className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span
                  className={cn(
                    'absolute inline-flex h-full w-full animate-ping rounded-full opacity-75',
                    allUp ? 'bg-emerald-400' : 'bg-amber-400',
                  )}
                />
                <span className={cn('relative inline-flex h-2 w-2 rounded-full', allUp ? 'bg-emerald-400' : 'bg-amber-400')} />
              </span>
              <span className={cn('text-[10px] font-semibold uppercase tracking-widest', allUp ? 'text-emerald-300' : 'text-amber-300')}>
                {allUp ? 'All Systems' : 'Degraded'}
              </span>
            </span>
            <span className={cn('font-mono text-xs font-bold', allUp ? 'text-emerald-300' : 'text-amber-300')}>
              {status.up}/{status.total}
            </span>
          </div>
        </div>
      )}

      {/* Nav */}
      <div className="px-4 pt-5 pb-2">
        <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[--text-muted]">Navigation</p>
      </div>
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 pb-3">
        {NAV_ITEMS.map(({ to, icon: Icon, label, iconBg, iconColor }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                'group relative flex items-center gap-3 rounded-lg px-2.5 py-2 text-sm transition-all duration-200',
                isActive
                  ? 'bg-white/[0.04] text-[--text-primary]'
                  : 'text-[--text-secondary] hover:bg-white/[0.02] hover:text-[--text-primary]',
              )
            }
          >
            {({ isActive }: { isActive: boolean }) => (
              <>
                {isActive && (
                  <span
                    aria-hidden
                    className="absolute left-0 top-1/2 h-7 w-[3px] -translate-y-1/2 rounded-r-full bg-gradient-to-b from-cyan-400 to-purple-500 shadow-[0_0_12px_rgba(0,229,255,0.6)]"
                  />
                )}
                <span
                  className={cn(
                    'flex h-8 w-8 shrink-0 items-center justify-center rounded-lg transition-all duration-200',
                    iconBg,
                    isActive ? 'ring-1 ring-white/10' : 'opacity-80 group-hover:opacity-100',
                  )}
                >
                  <Icon className={cn('h-4 w-4', iconColor)} strokeWidth={2.25} />
                </span>
                <span className={cn('font-medium tracking-tight', isActive && 'font-semibold')}>{label}</span>
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* User */}
      <div className="border-t border-white/[0.04] px-4 py-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex min-w-0 items-center gap-2.5">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-cyan-500/30 to-purple-600/30 ring-1 ring-white/10">
              <span className="text-xs font-bold uppercase text-cyan-200">{username?.[0] ?? '?'}</span>
            </div>
            <div className="min-w-0">
              <p className="truncate text-xs font-semibold text-[--text-primary]">{username}</p>
              <p className="font-mono text-[10px] tabular-nums text-[--text-muted]">
                {time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              </p>
            </div>
          </div>
          <button
            onClick={logout}
            title="Sign out"
            className="rounded-lg p-1.5 text-[--text-muted] transition-all hover:bg-red-500/10 hover:text-red-400"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </aside>
  );
}
