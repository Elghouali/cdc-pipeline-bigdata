import { useEffect, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { fetchMetrics } from '@/lib/api';
import type { Layer, MetricsResponse, TableMetric } from '@/types/api';
import { Badge } from '@/components/ui/Badge';
import { cn, formatNumber, formatRelativeTime } from '@/lib/utils';

const LAYERS: Layer[] = ['bronze', 'silver', 'gold'];

const LAYER_CFG: Record<Layer, {
  label: string;
  desc: string;
  color: string;
  badgeVariant: 'bronze' | 'muted' | 'warning';
}> = {
  bronze: { label: 'Bronze', desc: 'Raw ingested events from Debezium / Kafka', color: '#B08050', badgeVariant: 'bronze'  },
  silver: { label: 'Silver', desc: 'Deduplicated & type-cast records',           color: '#8B949E', badgeVariant: 'muted'   },
  gold:   { label: 'Gold',   desc: 'Business-level aggregated facts',            color: '#D29922', badgeVariant: 'warning' },
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
      setData(prev => ({ ...prev, [layer]: res }));
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
  const cfg = LAYER_CFG[activeLayer];
  const totalRows = current?.tables.reduce((s, t) => s + (t.row_count ?? 0), 0) ?? 0;
  const okCount = current?.tables.filter(t => !t.error).length ?? 0;
  const maxRows = Math.max(...(current?.tables.map(t => t.row_count ?? 0) ?? [1]), 1);

  return (
    <div className="page-enter p-6">
      {/* Header */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[--text-dim]">Medallion Architecture</p>
          <h1 className="mt-0.5 text-xl font-bold text-[--text-primary]">Data Layers</h1>
          <p className="mt-1 text-xs text-[--text-muted]">{cfg.desc}</p>
        </div>
        <button
          onClick={() => void load(activeLayer, true)}
          disabled={refreshing || loading}
          className="flex items-center gap-1.5 rounded-md border border-[--border] bg-[--bg-surface] px-3 py-1.5 text-[11px] text-[--text-muted] transition-colors hover:bg-[--bg-elevated] hover:text-[--text-primary] disabled:opacity-50"
        >
          <RefreshCw className={cn('h-3 w-3', refreshing && 'animate-spin')} />
          Refresh
        </button>
      </div>

      {/* Layer tabs */}
      <div className="mb-6 flex gap-2">
        {LAYERS.map(layer => {
          const c = LAYER_CFG[layer];
          const isActive = activeLayer === layer;
          return (
            <button
              key={layer}
              onClick={() => setActiveLayer(layer)}
              className={cn(
                'flex items-center gap-2 rounded-md border px-4 py-2 text-sm font-medium transition-all',
                isActive
                  ? 'text-[--text-primary]'
                  : 'border-[--border] bg-[--bg-surface] text-[--text-muted] hover:bg-[--bg-elevated] hover:text-[--text-primary]'
              )}
              style={isActive ? { borderColor: `${c.color}50`, backgroundColor: `${c.color}12`, color: c.color } : undefined}
            >
              <span
                className="h-2 w-2 rounded-full"
                style={{ backgroundColor: c.color, boxShadow: isActive ? `0 0 5px ${c.color}` : 'none' }}
              />
              {c.label}
            </button>
          );
        })}
      </div>

      {loading && (
        <>
          <div className="mb-4 grid grid-cols-3 gap-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="skeleton-shimmer h-20 rounded-lg" />
            ))}
          </div>
          <div className="rounded-lg border border-[--border] bg-[--bg-surface] overflow-hidden">
            <div className="border-b border-[--border] bg-[--bg-elevated] px-5 py-3">
              <div className="grid grid-cols-5 gap-4">
                {Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="skeleton-shimmer h-3 rounded" />
                ))}
              </div>
            </div>
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="border-b border-[--border-subtle] px-5 py-3 last:border-0">
                <div className="grid grid-cols-5 gap-4">
                  {Array.from({ length: 5 }).map((_, j) => (
                    <div key={j} className="skeleton-shimmer h-3 rounded" style={{ width: `${60 + j * 10}%` }} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {!loading && error && (
        <div className="rounded-lg border border-[#F85149]/30 bg-[#F85149]/8 px-4 py-3 text-sm text-[#F85149]">
          {error}
        </div>
      )}

      {!loading && !error && current && (
        <>
          {/* Summary stats */}
          <div className="mb-4 grid grid-cols-3 gap-4">
            <div className="rounded-lg border border-[--border] bg-[--bg-surface] p-5">
              <p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[--text-dim]">Total Rows</p>
              <p className="mt-1.5 font-mono text-3xl font-light text-[--text-primary]">{formatNumber(totalRows)}</p>
            </div>
            <div className="rounded-lg border border-[--border] bg-[--bg-surface] p-5">
              <p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[--text-dim]">Tables OK</p>
              <p className="mt-1.5 font-mono text-3xl font-light" style={{ color: cfg.color }}>
                {okCount}<span className="text-[--text-dim] text-lg">/{current.tables.length}</span>
              </p>
            </div>
            <div className="rounded-lg border border-[--border] bg-[--bg-surface] p-5">
              <p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[--text-dim]">Generated</p>
              <p className="mt-1.5 font-mono text-lg font-light text-[--text-primary]">
                {formatRelativeTime(current.generated_at)}
              </p>
              {current.cached && <Badge variant="muted" className="mt-1">Cached</Badge>}
            </div>
          </div>

          {/* Tables */}
          <div className="rounded-lg border border-[--border] bg-[--bg-surface] overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[--border] bg-[--bg-elevated]">
                  {['Table', 'Rows', 'Volume', 'Latest Partition', 'Status'].map((h, i) => (
                    <th
                      key={h}
                      className={cn(
                        'px-5 py-3 text-[10px] font-semibold uppercase tracking-[0.08em] text-[--text-dim]',
                        i === 1 ? 'text-right' : 'text-left',
                      )}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {current.tables.map(t => (
                  <TableRow key={t.table} metric={t} color={cfg.color} maxRows={maxRows} />
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

function TableRow({ metric, color, maxRows }: { metric: TableMetric; color: string; maxRows: number }) {
  const hasError = !!metric.error;
  const pct = hasError ? 0 : Math.max(((metric.row_count ?? 0) / maxRows) * 100, metric.row_count ? 1 : 0);

  return (
    <tr className="border-b border-[--border-subtle] transition-colors last:border-0 hover:bg-[--bg-elevated]">
      <td className="px-5 py-3">
        <div className="flex items-center gap-2">
          <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: hasError ? '#F85149' : color }} />
          <span className="font-mono text-[11px] text-[--text-primary]">{metric.table}</span>
        </div>
      </td>
      <td className="px-5 py-3 text-right font-mono text-sm tabular-nums text-[--text-primary]">
        {hasError ? <span className="text-[--text-dim]">—</span> : formatNumber(metric.row_count)}
      </td>
      <td className="w-36 px-5 py-3">
        <div className="h-1 w-full overflow-hidden rounded-full bg-[--bg-elevated]">
          <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: color }} />
        </div>
      </td>
      <td className="px-5 py-3 font-mono text-[11px] text-[--text-muted]">
        {metric.latest_partition ?? '—'}
      </td>
      <td className="px-5 py-3">
        <Badge variant={hasError ? 'error' : 'success'}>{hasError ? 'Error' : 'OK'}</Badge>
      </td>
    </tr>
  );
}
