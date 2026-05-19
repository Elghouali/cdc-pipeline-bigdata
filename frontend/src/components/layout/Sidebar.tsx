import { NavLink } from 'react-router-dom';
import {
  Activity,
  BarChart3,
  Database,
  LayoutDashboard,
  LogOut,
  Zap,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/context/AuthContext';

interface NavItem {
  to: string;
  icon: React.ElementType;
  label: string;
}

const NAV_ITEMS: NavItem[] = [
  { to: '/health',    icon: Activity,        label: 'Pipeline Health' },
  { to: '/metrics',   icon: Database,        label: 'Data Layers'     },
  { to: '/dashboard', icon: LayoutDashboard, label: 'KPI Dashboard'   },
  { to: '/stats',     icon: BarChart3,       label: 'Spark Jobs'      },
];

export function Sidebar() {
  const { username, logout } = useAuth();

  return (
    <aside className="flex h-screen w-56 shrink-0 flex-col border-r border-[--border] bg-[--bg-surface]">
      {/* Logo */}
      <div className="flex items-center gap-2.5 border-b border-[--border] px-4 py-4">
        <div className="flex h-7 w-7 items-center justify-center rounded-md bg-cyan-500/20">
          <Zap className="h-4 w-4 text-cyan-400" />
        </div>
        <div>
          <p className="text-sm font-semibold text-[--text-primary]">CDC Pipeline</p>
          <p className="text-[10px] text-[--text-muted]">Medallion Console</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 py-3">
        {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors',
                isActive
                  ? 'bg-cyan-500/15 text-cyan-300 font-medium'
                  : 'text-[--text-secondary] hover:bg-[--bg-hover] hover:text-[--text-primary]',
              )
            }
          >
            <Icon className="h-4 w-4 shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* User */}
      <div className="border-t border-[--border] px-3 py-3">
        <div className="flex items-center justify-between">
          <div className="min-w-0">
            <p className="truncate text-xs font-medium text-[--text-primary]">{username}</p>
            <p className="text-[10px] text-[--text-muted]">Signed in</p>
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
