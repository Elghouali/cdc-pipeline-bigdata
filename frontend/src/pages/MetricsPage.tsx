import { useEffect, useState } from 'react';
import { RefreshCw, Server } from 'lucide-react';
import { fetchMetrics } from '@/lib/api';
import type { Layer, MetricsResponse, TableMetric } from '@/types/api';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Skeleton, SkeletonTableRow } from '@/components/ui/Skeleton';
import { Button } from '@/components/ui/Button';
import { formatNumber, formatRelativeTime } from '@/lib/utils';

const LAYERS: Layer[] = ['bronze', 'silver', 'gold'];

const LAYER_META: Record<Layer, { label: string; desc: string }> = {
  bronze: { label: 'Bronze', desc: 'Raw ingested events from Debezium/Kafka' },
  silver: { label: 'Silver', desc: 'Deduplicated & type-cast records'        },
  gold:   { label: 'Gold',   desc: 'Business-level aggregated facts'         },
};

const LAYER_STYLE: Record<Layer, { dot: string; bar: string; text: string }> = {
  bronze: { dot: 'bg-amber-400',   bar: 'bg-amber-400',   text: 'text-amber-400'   },
  silver: { dot: 'bg-cyan-400',    bar: 'bg-cyan-400',    text: 'text-cyan-400'    },
  gold:   { dot: 'bg-emerald-400', bar: 'bg-emerald-400', text: 'text-emerald-400' },
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
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-[--text-primary]">Data Layers</h1>
          <p className="text-xs text-[--text-muted]">{meta.desc}</p>
        </div>
        <button
          onClick={() => void load(activeLayer, true)}
          disabled={refreshing || loading}
          title="Refresh"
          className="rounded-md p-2 text-[--text-muted] transition-colors hover:bg-[--bg-elevated] hover:text-[--text-primary] disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Layer tabs */}
      <div className="mb-5 flex gap-2">
        {LAYERS.map((layer) => (
          <Button
            key={layer}
            variant={activeLayer === layer ? 'primary' : 'outline'}
            size="sm"
            onClick={() => setActiveLayer(layer)}
          >
            <span className={`h-2 w-2 rounded-full ${LAYER_STYLE[layer].dot}`} />
            {LAYER_META[layer].label}
          </Button>
        ))}
      </div>

      {loading && (
        <>
          <div className="mb-4 grid grid-cols-3 gap-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-20 rounded-lg" />
            ))}
          </div>
          <Card className="overflow-hidden p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[--border] bg-[--bg-elevated]">
                  {['Table', 'Rows', 'Volume', 'Latest Partition', 'Status'].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[--text-muted]">
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
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {!loading && !error && current && (
        <>
          {/* Summary stats */}
          <div className="mb-4 grid grid-cols-3 gap-3">
            <div className="rounded-lg border border-[--border] bg-[--bg-surface] px-4 py-3">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-[--text-muted]">Total Rows</p>
              <p className={`mt-1 font-mono text-xl font-bold ${style.text}`}>{formatNumber(totalRows)}</p>
            </div>
            <div className="rounded-lg border border-[--border] bg-[--bg-surface] px-4 py-3">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-[--text-muted]">Tables OK</p>
              <p className={`mt-1 font-mono text-xl font-bold ${style.text}`}>{okCount}/{current.tables.length}</p>
            </div>
            <div className="rounded-lg border border-[--border] bg-[--bg-surface] px-4 py-3">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-[--text-muted]">Updated</p>
              <p className="mt-1 font-mono text-xl font-bold text-[--text-secondary]">{formatRelativeTime(current.generated_at)}</p>
            </div>
          </div>

          <div className="mb-3 flex items-center gap-3 text-xs text-[--text-muted]">
            <Server className="h-3.5 w-3.5" />
            <span>{current.tables.length} tables</span>
            {current.cached && <Badge variant="muted">Cached</Badge>}
          </div>

          <Card className="overflow-hidden p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[--border] bg-[--bg-elevated]">
                  {['Table', 'Rows', 'Volume', 'Latest Partition', 'Status'].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[--text-muted]">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {current.tables.map((t, i) => (
                  <TableRow key={t.table} metric={t} layer={activeLayer} stripe={i % 2 === 1} maxRows={maxRows} />
                ))}
              </tbody>
            </table>
          </Card>
        </>
      )}
    </div>
  );
}

function TableRow({ metric, layer, stripe, maxRows }: {
  metric: TableMetric; layer: Layer; stripe: boolean; maxRows: number;
}) {
  const hasError = !!metric.error;
  const style = LAYER_STYLE[layer];
  const pct = hasError ? 0 : Math.max(((metric.row_count ?? 0) / maxRows) * 100, metric.row_count ? 2 : 0);

  return (
    <tr className={`border-b border-[--border] last:border-0 ${stripe ? 'bg-[--bg-elevated]/40' : ''}`}>
      <td className="px-4 py-3 font-mono text-xs text-[--text-primary]">
        <span className="flex items-center gap-2">
          <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${style.dot}`} />
          {metric.table}
        </span>
      </td>
      <td className="px-4 py-3 font-mono text-xs font-medium text-[--text-secondary] tabular-nums">
        {hasError ? '—' : formatNumber(metric.row_count)}
      </td>
      <td className="w-36 px-4 py-3">
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-[--bg-elevated]">
          <div className={`h-full rounded-full transition-all duration-700 ${style.bar}`} style={{ width: `${pct}%` }} />
        </div>
      </td>
      <td className="px-4 py-3 font-mono text-xs text-[--text-muted]">
        {metric.latest_partition ?? '—'}
      </td>
      <td className="px-4 py-3">
        {hasError ? <Badge variant="error">Error</Badge> : <Badge variant="success">OK</Badge>}
      </td>
    </tr>
  );
}
