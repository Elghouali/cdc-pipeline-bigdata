import { useEffect, useState } from 'react';
import { Clock, Database, HardDrive, RefreshCw, Server, XCircle, Layers } from 'lucide-react';
import { fetchHealth } from '@/lib/api';
import type { HealthItem } from '@/types/api';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { SkeletonCard } from '@/components/ui/Skeleton';
import { formatLatency, formatRelativeTime } from '@/lib/utils';

interface ServiceColor {
  accent: string;
  bg: string;
  strip: string;
  bar: string;
  ring: string;
}

const SERVICE_COLORS: Record<string, ServiceColor> = {
  postgres:        { accent: 'text-blue-300',    bg: 'bg-blue-500/15',    strip: 'from-blue-400 to-blue-600',       bar: 'bg-blue-400',    ring: 'ring-blue-500/30'    },
  trino:           { accent: 'text-purple-300',  bg: 'bg-purple-500/15',  strip: 'from-purple-400 to-purple-600',   bar: 'bg-purple-400',  ring: 'ring-purple-500/30'  },
  'kafka-connect': { accent: 'text-red-300',     bg: 'bg-red-500/15',     strip: 'from-red-400 to-orange-500',      bar: 'bg-red-400',     ring: 'ring-red-500/30'     },
  'spark-master':  { accent: 'text-amber-300',   bg: 'bg-amber-500/15',   strip: 'from-amber-400 to-yellow-500',    bar: 'bg-amber-400',   ring: 'ring-amber-500/30'   },
  minio:           { accent: 'text-emerald-300', bg: 'bg-emerald-500/15', strip: 'from-emerald-400 to-teal-500',    bar: 'bg-emerald-400', ring: 'ring-emerald-500/30' },
};

const DEFAULT_COLOR: ServiceColor = {
  accent: 'text-cyan-300', bg: 'bg-cyan-500/15', strip: 'from-cyan-400 to-cyan-600', bar: 'bg-cyan-400', ring: 'ring-cyan-500/30',
};

const SERVICE_META: Record<string, { label: string; icon: React.ElementType; desc: string }> = {
  postgres:        { label: 'PostgreSQL',    icon: Database,  desc: 'Source database · WAL logical replication'        },
  trino:           { label: 'Trino',         icon: Layers,    desc: 'Distributed SQL · queries Iceberg on MinIO'       },
  'kafka-connect': { label: 'Kafka Connect', icon: Server,    desc: 'Debezium CDC · captures row-level changes'        },
  'spark-master':  { label: 'Spark Master',  icon: Server,    desc: 'Streaming orchestration · Bronze → Silver → Gold' },
  minio:           { label: 'MinIO',         icon: HardDrive, desc: 'Object storage · Parquet + Iceberg metadata'      },
};

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
    <div className="page-enter p-8">
      {/* Header */}
      <div className="mb-7 flex items-end justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.25em] text-[--text-muted]">
            Infrastructure
          </p>
          <h1 className="mt-1 text-2xl font-black tracking-tight text-[--text-primary]">
            Pipeline <span className="gradient-text">Health</span>
          </h1>
          <p className="mt-1 text-xs text-[--text-muted]">
            {lastUpdated ? `Updated ${formatRelativeTime(lastUpdated)}` : 'Loading…'}
            &ensp;·&ensp;auto-refresh every 10s
          </p>
        </div>
        <button
          onClick={() => void load(true)}
          disabled={refreshing}
          title="Refresh now"
          className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-2.5 text-[--text-muted] transition-all hover:border-cyan-500/40 hover:bg-white/[0.04] hover:text-cyan-300 disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Status banner */}
      {!loading && items.length > 0 && (
        <div
          className={`relative mb-6 overflow-hidden rounded-2xl border p-5 ${
            allUp
              ? 'border-emerald-500/20 bg-gradient-to-r from-emerald-500/[0.08] via-cyan-500/[0.04] to-transparent'
              : 'border-amber-500/25 bg-gradient-to-r from-amber-500/[0.10] via-red-500/[0.04] to-transparent'
          }`}
        >
          <div aria-hidden className={`pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r ${allUp ? 'from-transparent via-emerald-400/80 to-transparent' : 'from-transparent via-amber-400/80 to-transparent'}`} />
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <span className="relative flex h-3 w-3">
                <span className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-60 ${allUp ? 'bg-emerald-400' : 'bg-amber-400'}`} />
                <span className={`relative inline-flex h-3 w-3 rounded-full ${allUp ? 'bg-emerald-400' : 'bg-amber-400'} shadow-[0_0_12px_currentColor]`} />
              </span>
              <div>
                <p className={`text-xl font-black tracking-tight ${allUp ? 'gradient-text-success' : 'text-amber-300'}`}>
                  {allUp ? 'ALL SYSTEMS OPERATIONAL' : `${upCount}/${items.length} SERVICES UP`}
                </p>
                <p className="mt-0.5 text-[11px] font-medium uppercase tracking-widest text-[--text-muted]">
                  {allUp ? 'Pipeline is healthy' : 'Investigate degraded services below'}
                </p>
              </div>
            </div>
            <div className="hidden text-right sm:block">
              <p className="font-mono text-3xl font-black text-[--text-primary]">
                {upCount}<span className="text-[--text-muted]">/{items.length}</span>
              </p>
              <p className="text-[10px] font-semibold uppercase tracking-widest text-[--text-muted]">
                services online
              </p>
            </div>
          </div>
        </div>
      )}

      {loading && (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 5 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
      )}

      {!loading && error && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      {!loading && !error && (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((item) => <ServiceCard key={item.service} item={item} />)}
        </div>
      )}
    </div>
  );
}

function ServiceCard({ item }: { item: HealthItem }) {
  const isUp = item.status === 'up';
  const meta = SERVICE_META[item.service] ?? { label: item.service, icon: Server, desc: '' };
  const colors = SERVICE_COLORS[item.service] ?? DEFAULT_COLOR;
  const Icon = meta.icon;

  return (
    <Card variant="glass" className="relative overflow-hidden transition-all hover:-translate-y-0.5 hover:ring-1 hover:ring-white/10">
      {/* Top gradient strip */}
      <div className={`pointer-events-none absolute inset-x-0 top-0 h-[3px] bg-gradient-to-r ${colors.strip} ${!isUp && 'opacity-30'}`} />
      {/* Corner glow */}
      <div className={`pointer-events-none absolute -right-12 -top-12 h-32 w-32 rounded-full blur-3xl opacity-30 ${colors.bg}`} />

      <CardHeader>
        <div className="flex items-center gap-2.5">
          <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${colors.bg} ring-1 ${colors.ring}`}>
            <Icon className={`h-4 w-4 ${colors.accent}`} strokeWidth={2.25} />
          </div>
          <div>
            <CardTitle className="!text-[10px]">{item.service}</CardTitle>
            <p className="text-sm font-semibold text-[--text-primary]">{meta.label}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isUp ? (
            <span className="relative flex h-2.5 w-2.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
              <span className="absolute inline-flex h-full w-full rounded-full bg-emerald-400/40 blur-sm" />
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(16,255,170,0.8)]" />
            </span>
          ) : (
            <XCircle className="h-4 w-4 text-red-400" />
          )}
          <Badge variant={isUp ? 'success' : 'error'}>{isUp ? 'UP' : 'DOWN'}</Badge>
        </div>
      </CardHeader>

      {meta.desc && (
        <p className="mb-4 text-[11px] leading-relaxed text-[--text-muted]">{meta.desc}</p>
      )}

      {/* Big latency */}
      <div className="mb-3 flex items-baseline justify-between">
        <span className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-widest text-[--text-muted]">
          <Clock className="h-3 w-3" />
          Latency
        </span>
        <span className={`font-mono text-3xl font-black tracking-tight ${isUp ? colors.accent : 'text-[--text-muted]'}`}>
          {item.latency_ms !== null ? (
            <>
              {item.latency_ms.toFixed(0)}
              <span className="ml-1 text-xs font-semibold text-[--text-muted]">ms</span>
            </>
          ) : (
            formatLatency(item.latency_ms)
          )}
        </span>
      </div>

      <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/[0.04]">
        <div
          className={`h-full rounded-full transition-all duration-700 ${isUp ? colors.bar : 'bg-red-400'}`}
          style={{ width: `${latencyPct(item.latency_ms)}%` }}
        />
      </div>

      {item.detail && (
        <p className="mt-3 rounded-lg border border-red-500/20 bg-red-500/10 px-2.5 py-1.5 font-mono text-[11px] leading-snug text-red-300">
          {item.detail}
        </p>
      )}
    </Card>
  );
}
