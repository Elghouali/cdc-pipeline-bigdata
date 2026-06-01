import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { RefreshCw } from 'lucide-react';
import { fetchHealth } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import { cn } from '@/lib/utils';

const ROUTE_LABELS: Record<string, string> = {
  '/dashboard': 'Overview',
  '/bronze':    'Bronze Layer',
  '/silver':    'Silver Layer',
  '/gold':      'Gold Layer',
  '/stream':    'Event Stream',
  '/query':     'Query Console',
};

export function TopBar() {
  const { pathname } = useLocation();
  const { username, logout } = useAuth();
  const [upCount, setUpCount] = useState<number | null>(null);
  const [totalCount, setTotalCount] = useState<number | null>(null);
  const [avgLatency, setAvgLatency] = useState<number | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [refreshing, setRefreshing] = useState(false);

  async function poll() {
    setRefreshing(true);
    try {
      const items = await fetchHealth();
      const up = items.filter(i => i.status === 'up');
      setUpCount(up.length);
      setTotalCount(items.length);
      const latencies = up.map(i => i.latency_ms).filter((l): l is number => l !== null);
      if (latencies.length > 0) {
        setAvgLatency(Math.round(latencies.reduce((a, b) => a + b, 0) / latencies.length));
      }
      setLastRefresh(new Date());
    } catch {
      /* keep previous */
    } finally {
      setRefreshing(false);
    }
  }

  useEffect(() => {
    void poll();
    const id = setInterval(() => void poll(), 30_000);
    return () => clearInterval(id);
  }, []);

  const isAllUp = upCount !== null && totalCount !== null && upCount === totalCount && totalCount > 0;
  const isDegraded = upCount !== null && totalCount !== null && upCount < totalCount && upCount > 0;
  const isDown = upCount === 0;

  const statusLabel = isAllUp ? 'All systems live' : isDegraded ? 'Degraded' : isDown ? 'Pipeline down' : 'Checking…';
  const statusColor = isAllUp ? 'var(--accent-green)' : isDegraded ? 'var(--accent-yellow)' : isDown ? 'var(--accent-red)' : 'var(--text-dim)';
  const statusBg = isAllUp ? 'rgba(52,211,153,0.08)' : isDegraded ? 'rgba(252,211,77,0.08)' : isDown ? 'rgba(248,113,113,0.08)' : 'var(--bg-elevated)';
  const statusBorder = isAllUp ? 'rgba(52,211,153,0.25)' : isDegraded ? 'rgba(252,211,77,0.25)' : isDown ? 'rgba(248,113,113,0.25)' : 'var(--border)';

  const label = ROUTE_LABELS[pathname] ?? 'Dashboard';

  function formatLastRefresh() {
    const diff = Math.round((Date.now() - lastRefresh.getTime()) / 1000);
    if (diff < 5) return 'just now';
    if (diff < 60) return `${diff}s ago`;
    return `${Math.floor(diff / 60)}m ago`;
  }

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-[--border] bg-[--bg-surface] px-6">
      {/* Left: breadcrumb */}
      <div className="flex items-center gap-2 text-sm">
        <span className="font-medium text-[--text-muted]">CDC Pipeline</span>
        <span className="text-[--border] select-none">/</span>
        <span className="font-semibold text-[--text-primary]">{label}</span>
      </div>

      {/* Center: status pill */}
      <div
        className="flex items-center gap-2 rounded-full border px-3 py-1.5 text-[12px] font-medium transition-colors"
        style={{ borderColor: statusBorder, backgroundColor: statusBg, color: statusColor }}
      >
        <span
          className="h-1.5 w-1.5 rounded-full"
          style={{ backgroundColor: statusColor }}
        />
        <span>{statusLabel}</span>
        {upCount !== null && totalCount !== null && (
          <span className="font-mono opacity-60">{upCount}/{totalCount}</span>
        )}
      </div>

      {/* Right: metrics + avatar */}
      <div className="flex items-center gap-4">
        {avgLatency !== null && (
          <div className="flex items-center gap-1.5">
            <span className="text-[11px] text-[--text-dim]">Avg latency</span>
            <span className={cn(
              'font-mono text-[12px] font-semibold',
              avgLatency < 100 ? 'text-[--accent-green]' :
              avgLatency < 300 ? 'text-[--accent-yellow]' : 'text-[--accent-red]'
            )}>
              {avgLatency}ms
            </span>
          </div>
        )}
        <div className="flex items-center gap-1.5 text-[11px] text-[--text-dim]">
          <RefreshCw className={cn('h-3 w-3', refreshing && 'animate-spin')} />
          <span className="font-mono">{formatLastRefresh()}</span>
        </div>
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-[--accent] text-[10px] font-bold uppercase text-white">
            {username?.[0] ?? '?'}
          </div>
          <span className="text-[12px] font-medium text-[--text-secondary]">{username}</span>
          <button
            onClick={logout}
            className="text-[11px] text-[--text-dim] transition-colors hover:text-[--accent-red] ml-1"
          >
            Sign out
          </button>
        </div>
      </div>
    </header>
  );
}
