import { NavLink } from 'react-router-dom';
import { Activity, Database, LayoutDashboard, LogOut, Workflow, Zap } from 'lucide-react';
import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/context/AuthContext';
import { fetchHealth } from '@/lib/api';

interface NavItem { to: string; icon: React.ElementType; label: string; }

const NAV_ITEMS: NavItem[] = [
  { to: '/health',    icon: Activity,        label: 'Pipeline Health' },
  { to: '/metrics',   icon: Database,        label: 'Data Layers'     },
  { to: '/dashboard', icon: LayoutDashboard, label: 'KPI Dashboard'   },
  { to: '/stats',     icon: Workflow,        label: 'Overview'        },
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
    <aside className="flex h-screen w-56 shrink-0 flex-col border-r border-[--border] bg-[--bg-surface]">
      {/* Logo */}
      <div className="flex items-center gap-2.5 border-b border-[--border] px-4 py-4">
        <div className="flex h-7 w-7 items-center justify-center rounded-md bg-cyan-500/20">
          <Zap className="h-4 w-4 text-cyan-400" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-[--text-primary]">CDC Pipeline</p>
          <p className="text-[10px] text-[--text-muted]">Medallion Console</p>
        </div>
        {status && (
          <div className="flex items-center gap-1.5 shrink-0">
            <span className="relative flex h-1.5 w-1.5">
              {allUp && <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />}
              <span className={`relative inline-flex h-1.5 w-1.5 rounded-full ${allUp ? 'bg-emerald-400' : 'bg-amber-400'}`} />
            </span>
            <span className={`text-[10px] font-mono font-bold ${allUp ? 'text-emerald-400' : 'text-amber-400'}`}>
              {status.up}/{status.total}
            </span>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 py-3">
        {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                'relative flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors',
                isActive
                  ? 'bg-cyan-500/15 text-cyan-300 font-medium'
                  : 'text-[--text-secondary] hover:bg-[--bg-hover] hover:text-[--text-primary]',
              )
            }
          >
            {({ isActive }: { isActive: boolean }) => (
              <>
                {isActive && (
                  <span className="absolute left-0 top-1/2 h-[18px] w-[3px] -translate-y-1/2 rounded-r-full bg-cyan-400" />
                )}
                <Icon className="h-4 w-4 shrink-0" />
                {label}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* User */}
      <div className="border-t border-[--border] px-3 py-3">
        <div className="flex items-center justify-between">
          <div className="min-w-0">
            <p className="truncate text-xs font-medium text-[--text-primary]">{username}</p>
            <p className="font-mono text-[10px] tabular-nums text-[--text-muted]">
              {time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </p>
          </div>
          <button
            onClick={logout}
            title="Sign out"
            className="rounded-md p-1.5 text-[--text-muted] transition-colors hover:bg-[--bg-hover] hover:text-red-400"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </aside>
  );
}
