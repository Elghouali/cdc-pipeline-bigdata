import { useEffect, useState } from 'react';
import { Clock, Database, HardDrive, RefreshCw, Server, XCircle, Layers } from 'lucide-react';
import { fetchHealth } from '@/lib/api';
import type { HealthItem } from '@/types/api';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { SkeletonCard } from '@/components/ui/Skeleton';
import { formatLatency, formatRelativeTime } from '@/lib/utils';

const SERVICE_META: Record<string, { label: string; icon: React.ElementType; desc: string }> = {
  postgres:        { label: 'PostgreSQL',    icon: Database,  desc: 'Source database · WAL logical replication'        },
  trino:           { label: 'Trino',         icon: Layers,    desc: 'Distributed SQL · queries Iceberg on MinIO'       },
  'kafka-connect': { label: 'Kafka Connect', icon: Server,    desc: 'Debezium CDC connector · captures row changes'    },
  'spark-master':  { label: 'Spark Master',  icon: Server,    desc: 'Streaming orchestration · Bronze → Silver → Gold' },
  minio:           { label: 'MinIO',         icon: HardDrive, desc: 'Object storage · Parquet + Iceberg metadata'      },
};

function latencyBarColor(ms: number | null): string {
  if (ms === null) return 'bg-[--border]';
  if (ms < 100) return 'bg-emerald-400';
  if (ms < 300) return 'bg-amber-400';
  return 'bg-red-400';
}

function latencyPct(ms: number | null): number {
  if (ms === null) return 0;
  return Math.min((ms / 500) * 100, 100);
}

const POLL_MS = 10_000;

export function HealthPage() {
  const [items, setItems] = useState<HealthItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [lastUpdated, setLastUpdated] = useState('');
  const [refreshing, setRefreshing] = useState(false);

  async function load(isManual = false) {
    if (isManual) setRefreshing(true);
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
    const id = setInterval(() => void load(), POLL_MS);
    return () => clearInterval(id);
  }, []);

  const upCount = items.filter((i) => i.status === 'up').length;
  const allUp = upCount === items.length && items.length > 0;

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-[--text-primary]">Pipeline Health</h1>
          <p className="text-xs text-[--text-muted]">
            {lastUpdated ? `Updated ${formatRelativeTime(lastUpdated)}` : 'Loading…'}
            &ensp;·&ensp;auto-refreshes every 10s
          </p>
        </div>
        <div className="flex items-center gap-3">
          {items.length > 0 && (
            <div className="flex items-center gap-2 rounded-lg border border-[--border] bg-[--bg-surface] px-3 py-1.5">
              <span className="relative flex h-2 w-2">
                {allUp && <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />}
                <span className={`relative inline-flex h-2 w-2 rounded-full ${allUp ? 'bg-emerald-400' : 'bg-amber-400'}`} />
              </span>
              <span className={`font-mono text-sm font-bold ${allUp ? 'text-emerald-400' : 'text-amber-400'}`}>
                {upCount}/{items.length}
              </span>
              <span className="text-xs text-[--text-muted]">services</span>
            </div>
          )}
          <button
            onClick={() => void load(true)}
            disabled={refreshing}
            title="Refresh now"
            className="rounded-md p-2 text-[--text-muted] transition-colors hover:bg-[--bg-elevated] hover:text-[--text-primary] disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {loading && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 5 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
      )}

      {!loading && error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {!loading && !error && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((item) => <ServiceCard key={item.service} item={item} />)}
        </div>
      )}
    </div>
  );
}

function ServiceCard({ item }: { item: HealthItem }) {
  const isUp = item.status === 'up';
  const meta = SERVICE_META[item.service] ?? { label: item.service, icon: Server, desc: '' };
  const Icon = meta.icon;

  return (
    <Card
      glow={isUp ? 'emerald' : 'none'}
      className="relative overflow-hidden transition-all hover:border-[--border-focus]"
    >
      <div className={`absolute inset-x-0 top-0 h-0.5 ${isUp ? 'bg-emerald-400/60' : 'bg-red-400/40'}`} />

      <CardHeader>
        <div className="flex items-center gap-2">
          <div className={`flex h-7 w-7 items-center justify-center rounded-md ${isUp ? 'bg-emerald-500/15' : 'bg-red-500/15'}`}>
            <Icon className={`h-3.5 w-3.5 ${isUp ? 'text-emerald-400' : 'text-red-400'}`} />
          </div>
          <CardTitle>{meta.label}</CardTitle>
        </div>
        <div className="flex items-center gap-1.5">
          {isUp ? (
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
            </span>
          ) : (
            <XCircle className="h-3.5 w-3.5 text-red-400" />
          )}
          <Badge variant={isUp ? 'success' : 'error'}>{isUp ? 'UP' : 'DOWN'}</Badge>
        </div>
      </CardHeader>

      {meta.desc && (
        <p className="mb-3 text-[11px] leading-relaxed text-[--text-muted]">{meta.desc}</p>
      )}

      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="flex items-center gap-1.5 text-[--text-muted]">
            <Clock className="h-3 w-3" />
            Latency
          </span>
          <span className={`font-mono font-medium ${
            item.latency_ms !== null && item.latency_ms < 100 ? 'text-emerald-400' :
            item.latency_ms !== null && item.latency_ms < 300 ? 'text-amber-400' :
            'text-[--text-secondary]'
          }`}>
            {formatLatency(item.latency_ms)}
          </span>
        </div>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-[--bg-elevated]">
          <div
            className={`h-full rounded-full transition-all duration-700 ${latencyBarColor(item.latency_ms)}`}
            style={{ width: `${latencyPct(item.latency_ms)}%` }}
          />
        </div>

        {item.detail && (
          <p className="mt-1 rounded border border-red-500/20 bg-red-500/10 px-2 py-1 font-mono text-[11px] leading-snug text-red-400">
            {item.detail}
          </p>
        )}
      </div>
    </Card>
  );
}
