import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { RefreshCw, Zap } from 'lucide-react';
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
      // keep previous
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

  const statusLabel = isAllUp ? 'PIPELINE LIVE' : isDegraded ? 'DEGRADED' : isDown ? 'PIPELINE DOWN' : 'CHECKING…';
  const statusColor = isAllUp ? '#3FB950' : isDegraded ? '#D29922' : isDown ? '#F85149' : '#8B949E';

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
        <Zap className="h-4 w-4 text-[--accent-cyan]" strokeWidth={2.5} />
        <span className="font-semibold text-[--text-primary]">CDC Pipeline</span>
        <span className="text-[--text-dim]">/</span>
        <span className="text-[--text-muted]">{label}</span>
      </div>

      {/* Center: status pill */}
      <div
        className="flex items-center gap-2 rounded-full border px-3 py-1"
        style={{ borderColor: `${statusColor}40`, backgroundColor: `${statusColor}12` }}
      >
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full rounded-full node-glow" style={{ backgroundColor: statusColor }} />
          <span className="relative inline-flex h-2 w-2 rounded-full" style={{ backgroundColor: statusColor }} />
        </span>
        <span className="font-mono text-[11px] font-semibold uppercase tracking-[0.1em]" style={{ color: statusColor }}>
          {statusLabel}
        </span>
        {upCount !== null && totalCount !== null && (
          <span className="font-mono text-[10px] text-[--text-dim]">{upCount}/{totalCount}</span>
        )}
      </div>

      {/* Right: metrics + avatar */}
      <div className="flex items-center gap-4">
        {avgLatency !== null && (
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] uppercase tracking-[0.08em] text-[--text-dim]">Avg</span>
            <span className={cn(
              'font-mono text-xs font-semibold',
              avgLatency < 100 ? 'text-[--accent-green]' :
              avgLatency < 300 ? 'text-[--accent-yellow]' : 'text-[--accent-red]'
            )}>
              {avgLatency}ms
            </span>
          </div>
        )}
        <div className="flex items-center gap-1 text-[10px] text-[--text-dim]">
          <RefreshCw className={cn('h-3 w-3', refreshing && 'animate-spin')} />
          <span className="font-mono">{formatLastRefresh()}</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-[--bg-elevated] border border-[--border] text-[10px] font-bold uppercase text-[--accent-cyan]">
            {username?.[0] ?? '?'}
          </div>
          <button onClick={logout} className="text-[11px] text-[--text-dim] transition-colors hover:text-[--accent-red]">
            Sign out
          </button>
        </div>
      </div>
    </header>
  );
}
