import { useEffect, useState } from 'react';
import { RefreshCw, Server } from 'lucide-react';
import { fetchMetrics } from '@/lib/api';
import type { Layer, MetricsResponse, TableMetric } from '@/types/api';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Skeleton, SkeletonTableRow } from '@/components/ui/Skeleton';
import { cn, formatNumber, formatRelativeTime } from '@/lib/utils';

const LAYERS: Layer[] = ['bronze', 'silver', 'gold'];

const LAYER_META: Record<Layer, { label: string; desc: string }> = {
  bronze: { label: 'Bronze', desc: 'Raw ingested events from Debezium / Kafka'   },
  silver: { label: 'Silver', desc: 'Deduplicated & type-cast records'             },
  gold:   { label: 'Gold',   desc: 'Business-level aggregated facts'              },
};

const LAYER_STYLE: Record<Layer, {
  dot: string;
  bar: string;
  text: string;
  activeBg: string;
  activeBorder: string;
  activeText: string;
}> = {
  bronze: {
    dot: 'bg-amber-400', bar: 'bg-gradient-to-r from-amber-400 to-orange-500', text: 'text-amber-300',
    activeBg: 'bg-gradient-to-r from-amber-500/20 to-orange-500/10',
    activeBorder: 'border-amber-400/40', activeText: 'text-amber-200',
  },
  silver: {
    dot: 'bg-cyan-400', bar: 'bg-gradient-to-r from-cyan-400 to-blue-500', text: 'text-cyan-300',
    activeBg: 'bg-gradient-to-r from-cyan-500/20 to-blue-500/10',
    activeBorder: 'border-cyan-400/40', activeText: 'text-cyan-200',
  },
  gold: {
    dot: 'bg-emerald-400', bar: 'bg-gradient-to-r from-emerald-400 to-cyan-500', text: 'text-emerald-300',
    activeBg: 'bg-gradient-to-r from-emerald-500/20 to-cyan-500/10',
    activeBorder: 'border-emerald-400/40', activeText: 'text-emerald-200',
  },
};

export function MetricsPage() {
  const [activeLayer, setActiveLayer] = useState<Layer>('gold');
  const [data, setData] = useState<Partial<Record<Layer, MetricsResponse>>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [refreshing, setRefreshing] = useState(false);

  async function load(layer: Layer, manual = false) {
    if (manual) setRefreshing(true);
    setError('');
    try {
      const res = await fetchMetrics(layer);
      setData((prev) => ({ ...prev, [layer]: res }));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to fetch metrics');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    setLoading(true);
    void load(activeLayer);
  }, [activeLayer]);

  const current = data[activeLayer];
  const meta = LAYER_META[activeLayer];
  const style = LAYER_STYLE[activeLayer];

  const totalRows = current?.tables.reduce((s, t) => s + (t.row_count ?? 0), 0) ?? 0;
  const okCount = current?.tables.filter(t => !t.error).length ?? 0;
  const maxRows = Math.max(...(current?.tables.map(t => t.row_count ?? 0) ?? [1]), 1);

  return (
    <div className="page-enter p-8">
      <div className="mb-7 flex items-end justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.25em] text-[--text-muted]">
            Medallion Architecture
          </p>
          <h1 className="mt-1 text-2xl font-black tracking-tight text-[--text-primary]">
            Data <span className="gradient-text">Layers</span>
          </h1>
          <p className="mt-1 text-xs text-[--text-muted]">{meta.desc}</p>
        </div>
        <button
          onClick={() => void load(activeLayer, true)}
          disabled={refreshing || loading}
          title="Refresh"
          className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-2.5 text-[--text-muted] transition-all hover:border-cyan-500/40 hover:bg-white/[0.04] hover:text-cyan-300 disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Layer tabs — pill gradient active */}
      <div className="mb-6 flex flex-wrap gap-2">
        {LAYERS.map((layer) => {
          const s = LAYER_STYLE[layer];
          const isActive = activeLayer === layer;
          return (
            <button
              key={layer}
              onClick={() => setActiveLayer(layer)}
              className={cn(
                'group inline-flex items-center gap-2.5 rounded-full border px-4 py-2 text-sm font-semibold tracking-tight transition-all',
                isActive
                  ? cn(s.activeBg, s.activeBorder, s.activeText, 'shadow-[0_0_24px_rgba(0,229,255,0.10)]')
                  : 'border-white/[0.06] bg-white/[0.02] text-[--text-secondary] hover:border-white/[0.12] hover:text-[--text-primary]',
              )}
            >
              <span className={cn('h-2 w-2 rounded-full', s.dot, isActive && 'shadow-[0_0_8px_currentColor]')} />
              {LAYER_META[layer].label}
              <span className="font-mono text-[10px] uppercase tracking-widest opacity-60">
                {layer === 'bronze' ? 'raw' : layer === 'silver' ? 'clean' : 'agg'}
              </span>
            </button>
          );
        })}
      </div>

      {loading && (
        <>
          <div className="mb-5 grid grid-cols-3 gap-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-24 rounded-xl" />
            ))}
          </div>
          <Card variant="glass" className="overflow-hidden !p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/[0.06]">
                  {['Table', 'Rows', 'Volume', 'Latest Partition', 'Status'].map((h) => (
                    <th key={h} className="px-5 py-3 text-left text-[10px] font-semibold uppercase tracking-widest text-[--text-muted]">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Array.from({ length: 6 }).map((_, i) => <SkeletonTableRow key={i} />)}
              </tbody>
            </table>
          </Card>
        </>
      )}

      {!loading && error && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      {!loading && !error && current && (
        <>
          {/* Summary stats */}
          <div className="mb-5 grid grid-cols-3 gap-4">
            <Card variant="glass" className="relative overflow-hidden">
              <div className={cn('pointer-events-none absolute -right-8 -top-8 h-24 w-24 rounded-full blur-2xl opacity-30', style.dot)} />
              <p className="text-[10px] font-semibold uppercase tracking-widest text-[--text-muted]">Total Rows</p>
              <p className="mt-1.5 font-mono text-3xl font-black tracking-tight gradient-text">{formatNumber(totalRows)}</p>
            </Card>
            <Card variant="glass" className="relative overflow-hidden">
              <p className="text-[10px] font-semibold uppercase tracking-widest text-[--text-muted]">Tables OK</p>
              <p className={cn('mt-1.5 font-mono text-3xl font-black tracking-tight', style.text)}>
                {okCount}<span className="text-[--text-muted]">/{current.tables.length}</span>
              </p>
            </Card>
            <Card variant="glass" className="relative overflow-hidden">
              <p className="text-[10px] font-semibold uppercase tracking-widest text-[--text-muted]">Updated</p>
              <p className="mt-1.5 font-mono text-2xl font-bold text-[--text-primary]">
                {formatRelativeTime(current.generated_at)}
              </p>
            </Card>
          </div>

          <div className="mb-3 flex items-center gap-3 text-[11px] font-medium text-[--text-muted]">
            <Server className="h-3.5 w-3.5" />
            <span className="uppercase tracking-widest">{current.tables.length} tables</span>
            {current.cached && <Badge variant="muted">Cached</Badge>}
          </div>

          <Card variant="glass" className="overflow-hidden !p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/[0.06]">
                  {['Table', 'Rows', 'Volume', 'Latest Partition', 'Status'].map((h, i) => (
                    <th
                      key={h}
                      className={cn(
                        'px-5 py-3.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-[--text-muted]',
                        i === 1 ? 'text-right' : 'text-left',
                      )}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {current.tables.map((t) => (
                  <TableRow key={t.table} metric={t} layer={activeLayer} maxRows={maxRows} />
                ))}
              </tbody>
            </table>
          </Card>
        </>
      )}
    </div>
  );
}

function TableRow({ metric, layer, maxRows }: {
  metric: TableMetric; layer: Layer; maxRows: number;
}) {
  const hasError = !!metric.error;
  const style = LAYER_STYLE[layer];
  const pct = hasError ? 0 : Math.max(((metric.row_count ?? 0) / maxRows) * 100, metric.row_count ? 2 : 0);

  return (
    <tr className="border-b border-white/[0.04] transition-colors last:border-0 hover:bg-white/[0.02]">
      <td className="px-5 py-3.5 font-mono text-xs text-[--text-primary]">
        <span className="flex items-center gap-2.5">
          <span className={cn('h-1.5 w-1.5 shrink-0 rounded-full shadow-[0_0_6px_currentColor]', style.dot)} />
          {metric.table}
        </span>
      </td>
      <td className="px-5 py-3.5 text-right font-mono text-sm font-semibold tabular-nums text-[--text-primary]">
        {hasError ? <span className="text-[--text-muted]">—</span> : formatNumber(metric.row_count)}
      </td>
      <td className="w-40 px-5 py-3.5">
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/[0.04]">
          <div className={cn('h-full rounded-full transition-all duration-700', style.bar)} style={{ width: `${pct}%` }} />
        </div>
      </td>
      <td className="px-5 py-3.5 font-mono text-xs text-[--text-muted]">
        {metric.latest_partition ?? '—'}
      </td>
      <td className="px-5 py-3.5">
        {hasError ? <Badge variant="error">Error</Badge> : <Badge variant="success">OK</Badge>}
      </td>
    </tr>
  );
}
