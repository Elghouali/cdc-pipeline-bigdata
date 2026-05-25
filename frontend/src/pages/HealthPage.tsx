import { useEffect, useState } from 'react';
import { Clock, RefreshCw } from 'lucide-react';
import { fetchHealth } from '@/lib/api';
import type { HealthItem } from '@/types/api';
import { cn, formatRelativeTime } from '@/lib/utils';
import { Badge } from '@/components/ui/Badge';

const SERVICE_META: Record<string, { label: string; desc: string; color: string }> = {
  postgres:        { label: 'PostgreSQL',    desc: 'WAL logical replication · Source DB',         color: '#58A6FF' },
  trino:           { label: 'Trino',         desc: 'Distributed SQL · Queries Iceberg on MinIO',  color: '#BC8CFF' },
  'kafka-connect': { label: 'Kafka Connect', desc: 'Debezium CDC · Row-level change capture',     color: '#FFA657' },
  'spark-master':  { label: 'Spark Master',  desc: 'Stream processing · Bronze→Silver→Gold',     color: '#D29922' },
  minio:           { label: 'MinIO',         desc: 'Object storage · Parquet + Iceberg metadata', color: '#3FB950' },
};

function latencyPct(ms: number | null): number {
  if (ms === null) return 0;
  return Math.min((ms / 500) * 100, 100);
}

export function HealthPage() {
  const [items, setItems] = useState<HealthItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [lastUpdated, setLastUpdated] = useState('');
  const [refreshing, setRefreshing] = useState(false);

  async function load(manual = false) {
    if (manual) setRefreshing(true);
    try {
      const data = await fetchHealth();
      setItems(data);
      setLastUpdated(new Date().toISOString());
      setError('');
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to fetch health data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    void load();
    const id = setInterval(() => void load(), 10_000);
    return () => clearInterval(id);
  }, []);

  const upCount = items.filter(i => i.status === 'up').length;
  const allUp = upCount === items.length && items.length > 0;

  return (
    <div className="page-enter p-6">
      <div className="mb-6 flex items-start justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[--text-dim]">Infrastructure</p>
          <h1 className="mt-0.5 text-xl font-bold text-[--text-primary]">Pipeline Health</h1>
          <p className="mt-1 text-xs text-[--text-muted]">
            {lastUpdated ? `Updated ${formatRelativeTime(lastUpdated)}` : 'Loading…'} · auto-refresh 10s
          </p>
        </div>
        <button
          onClick={() => void load(true)}
          disabled={refreshing}
          className="flex items-center gap-1.5 rounded-md border border-[--border] bg-[--bg-surface] px-3 py-1.5 text-[11px] text-[--text-muted] transition-colors hover:bg-[--bg-elevated] hover:text-[--text-primary] disabled:opacity-50"
        >
          <RefreshCw className={cn('h-3 w-3', refreshing && 'animate-spin')} />
          Refresh
        </button>
      </div>

      {!loading && items.length > 0 && (
        <div
          className="mb-6 flex items-center justify-between rounded-lg border p-4"
          style={{
            borderColor: allUp ? '#3FB95030' : '#D2992230',
            backgroundColor: allUp ? '#3FB95010' : '#D2992210',
          }}
        >
          <div className="flex items-center gap-3">
            <span className="relative flex h-3 w-3">
              <span className="absolute inline-flex h-full w-full rounded-full node-glow" style={{ backgroundColor: allUp ? '#3FB950' : '#D29922' }} />
              <span className="relative inline-flex h-3 w-3 rounded-full" style={{ backgroundColor: allUp ? '#3FB950' : '#D29922' }} />
            </span>
            <p className="font-semibold" style={{ color: allUp ? '#3FB950' : '#D29922' }}>
              {allUp ? 'ALL SYSTEMS OPERATIONAL' : `${upCount}/${items.length} SERVICES UP`}
            </p>
            <p className="text-sm text-[--text-muted]">
              {allUp ? 'Pipeline is healthy' : 'Investigate degraded services'}
            </p>
          </div>
          <p className="font-mono text-2xl font-light text-[--text-primary]">
            {upCount}<span className="text-[--text-dim]">/{items.length}</span>
          </p>
        </div>
      )}

      {loading && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="rounded-lg border border-[--border] bg-[--bg-surface] p-5 space-y-3">
              <div className="flex items-center gap-3">
                <div className="skeleton-shimmer h-9 w-9 rounded-lg" />
                <div className="flex-1 space-y-1.5">
                  <div className="skeleton-shimmer h-3 w-24 rounded" />
                  <div className="skeleton-shimmer h-3 w-36 rounded" />
                </div>
              </div>
              <div className="skeleton-shimmer h-7 w-20 rounded" />
              <div className="skeleton-shimmer h-1 w-full rounded-full" />
            </div>
          ))}
        </div>
      )}

      {!loading && error && (
        <div className="rounded-lg border border-[#F85149]/30 bg-[#F85149]/8 px-4 py-3 text-sm text-[#F85149]">
          {error}
        </div>
      )}

      {!loading && !error && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map(item => <ServiceCard key={item.service} item={item} />)}
        </div>
      )}
    </div>
  );
}

function ServiceCard({ item }: { item: HealthItem }) {
  const isUp = item.status === 'up';
  const meta = SERVICE_META[item.service] ?? { label: item.service, desc: '', color: '#8B949E' };

  return (
    <div
      className="rounded-lg border bg-[--bg-surface] p-5 transition-colors hover:bg-[--bg-elevated]"
      style={{
        borderColor: isUp ? `${meta.color}28` : '#F8514928',
        borderTopWidth: 2,
        borderTopColor: isUp ? meta.color : '#F85149',
      }}
    >
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <p className="font-semibold text-[--text-primary]">{meta.label}</p>
          <p className="mt-0.5 text-[11px] text-[--text-muted]">{meta.desc}</p>
        </div>
        <Badge variant={isUp ? 'success' : 'error'}>{isUp ? 'UP' : 'DOWN'}</Badge>
      </div>

      <div className="mb-2 flex items-baseline justify-between">
        <div className="flex items-center gap-1.5">
          <Clock className="h-3 w-3 text-[--text-dim]" />
          <span className="text-[10px] uppercase tracking-[0.08em] text-[--text-dim]">Latency</span>
        </div>
        <span
          className={cn(
            'font-mono text-2xl font-light',
            !isUp ? 'text-[#F85149]' :
            (item.latency_ms ?? 999) < 100 ? 'text-[--accent-green]' :
            (item.latency_ms ?? 999) < 300 ? 'text-[--accent-yellow]' : 'text-[--accent-red]'
          )}
        >
          {item.latency_ms !== null
            ? <>{item.latency_ms}<span className="ml-0.5 text-xs text-[--text-dim]">ms</span></>
            : '—'
          }
        </span>
      </div>

      <div className="h-1 w-full overflow-hidden rounded-full bg-[--bg-elevated]">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${latencyPct(item.latency_ms)}%`, backgroundColor: isUp ? meta.color : '#F85149' }}
        />
      </div>

      {item.detail && (
        <p className="mt-3 rounded-md border border-[#F85149]/20 bg-[#F85149]/8 px-2.5 py-1.5 font-mono text-[11px] text-[#F85149]">
          {item.detail}
        </p>
      )}
    </div>
  );
}
