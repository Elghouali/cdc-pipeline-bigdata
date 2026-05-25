import { useEffect, useState } from 'react';
import { ArrowRight, RefreshCw } from 'lucide-react';
import { fetchHealth, fetchMetrics } from '@/lib/api';
import type { HealthItem, Layer, MetricsResponse } from '@/types/api';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { Spinner } from '@/components/ui/Spinner';
import { formatNumber } from '@/lib/utils';

interface Stage {
  id: string;
  label: string;
  sublabel: string;
  serviceKey: string | null;
}

const PIPELINE_STAGES: Stage[] = [
  { id: 'postgres',   label: 'PostgreSQL',    sublabel: 'WAL source',       serviceKey: 'postgres'        },
  { id: 'debezium',   label: 'Debezium',      sublabel: 'CDC connector',    serviceKey: 'kafka-connect'   },
  { id: 'kafka',      label: 'Kafka',         sublabel: 'Event stream',     serviceKey: null              },
  { id: 'spark',      label: 'Spark',         sublabel: 'Stream processor', serviceKey: 'spark-master'    },
  { id: 'minio',      label: 'MinIO',         sublabel: 'Parquet/Iceberg',  serviceKey: 'minio'           },
];

const LAYERS: Layer[] = ['bronze', 'silver', 'gold'];

const LAYER_CFG: Record<Layer, { label: string; dot: string; bar: string; text: string; border: string }> = {
  bronze: { label: 'Bronze', dot: 'bg-amber-400',   bar: 'bg-amber-400',   text: 'text-amber-400',   border: 'border-amber-400/30' },
  silver: { label: 'Silver', dot: 'bg-cyan-400',    bar: 'bg-cyan-400',    text: 'text-cyan-400',    border: 'border-cyan-400/30'  },
  gold:   { label: 'Gold',   dot: 'bg-emerald-400', bar: 'bg-emerald-400', text: 'text-emerald-400', border: 'border-emerald-400/30' },
};

type LayerData = Partial<Record<Layer, MetricsResponse>>;

export function StatsPage() {
  const [health, setHealth]     = useState<HealthItem[]>([]);
  const [layers, setLayers]     = useState<LayerData>({});
  const [healthLoading, setHealthLoading] = useState(true);
  const [layersLoading, setLayersLoading] = useState(true);
  const [refreshing, setRefreshing]       = useState(false);

  async function loadAll(manual = false) {
    if (manual) setRefreshing(true);

    // health loads fast
    try {
      const h = await fetchHealth();
      setHealth(h);
    } catch {
      // keep previous
    } finally {
      setHealthLoading(false);
    }

    // layers hit Trino — use allSettled so one failure doesn't block others
    const results = await Promise.allSettled(
      LAYERS.map((l) => fetchMetrics(l))
    );
    setLayers((prev) => {
      const next = { ...prev };
      LAYERS.forEach((l, i) => {
        const r = results[i];
        if (r.status === 'fulfilled') next[l] = r.value;
      });
      return next;
    });
    setLayersLoading(false);
    setRefreshing(false);
  }

  useEffect(() => { void loadAll(); }, []);

  const healthMap = Object.fromEntries(health.map((h) => [h.service, h]));

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-[--text-primary]">Overview</h1>
          <p className="text-xs text-[--text-muted]">Pipeline topology · Medallion layer summary</p>
        </div>
        <button
          onClick={() => void loadAll(true)}
          disabled={refreshing}
          title="Refresh"
          className="rounded-md p-2 text-[--text-muted] transition-colors hover:bg-[--bg-elevated] hover:text-[--text-primary] disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Pipeline topology */}
      <Card className="mb-5">
        <CardHeader><CardTitle>Pipeline Topology</CardTitle></CardHeader>
        {healthLoading ? (
          <div className="flex h-16 items-center justify-center">
            <Spinner />
          </div>
        ) : (
          <div className="flex flex-wrap items-center gap-2">
            {PIPELINE_STAGES.map((stage, idx) => {
              const svc = stage.serviceKey ? healthMap[stage.serviceKey] : null;
              const isUp = svc?.status === 'up';
              const known = svc !== undefined;

              return (
                <div key={stage.id} className="flex items-center gap-2">
                  <div className={`rounded-lg border px-3 py-2 ${
                    !known    ? 'border-[--border] bg-[--bg-elevated]' :
                    isUp      ? 'border-emerald-400/40 bg-emerald-500/10' :
                                'border-red-400/40 bg-red-500/10'
                  }`}>
                    <div className="flex items-center gap-1.5">
                      <span className={`h-1.5 w-1.5 rounded-full ${
                        !known ? 'bg-[--text-muted]' :
                        isUp   ? 'bg-emerald-400' : 'bg-red-400'
                      }`} />
                      <span className="text-xs font-semibold text-[--text-primary]">{stage.label}</span>
                    </div>
                    <p className="mt-0.5 text-[10px] text-[--text-muted]">{stage.sublabel}</p>
                    {svc?.latency_ms != null && (
                      <p className={`mt-0.5 font-mono text-[10px] ${
                        svc.latency_ms < 100 ? 'text-emerald-400' :
                        svc.latency_ms < 300 ? 'text-amber-400'   : 'text-red-400'
                      }`}>{svc.latency_ms}ms</p>
                    )}
                  </div>
                  {idx < PIPELINE_STAGES.length - 1 && (
                    <ArrowRight className="h-3.5 w-3.5 shrink-0 text-[--text-muted]" />
                  )}
                </div>
              );
            })}

            {/* Iceberg tables */}
            <ArrowRight className="h-3.5 w-3.5 shrink-0 text-[--text-muted]" />
            <div className="flex items-center gap-1.5">
              {LAYERS.map((l, idx) => (
                <div key={l} className="flex items-center gap-1.5">
                  <div className={`rounded-lg border px-3 py-2 ${LAYER_CFG[l].border} bg-[--bg-elevated]`}>
                    <div className="flex items-center gap-1.5">
                      <span className={`h-1.5 w-1.5 rounded-full ${LAYER_CFG[l].dot}`} />
                      <span className="text-xs font-semibold text-[--text-primary]">{LAYER_CFG[l].label}</span>
                    </div>
                    <p className="mt-0.5 text-[10px] text-[--text-muted]">Iceberg</p>
                  </div>
                  {idx < LAYERS.length - 1 && (
                    <ArrowRight className="h-3 w-3 shrink-0 text-[--text-muted]" />
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </Card>

      {/* Medallion layers */}
      <div className="grid gap-4 lg:grid-cols-3">
        {LAYERS.map((l) => {
          const cfg  = LAYER_CFG[l];
          const data = layers[l];
          const maxRows = data
            ? Math.max(...data.tables.map((t) => t.row_count ?? 0), 1)
            : 1;
          const totalRows = data?.tables.reduce((s, t) => s + (t.row_count ?? 0), 0) ?? 0;

          return (
            <Card key={l} className={`border-t-2 ${cfg.border}`}>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <span className={`h-2 w-2 rounded-full ${cfg.dot}`} />
                  <CardTitle>{cfg.label} Layer</CardTitle>
                </div>
                {data && (
                  <span className={`font-mono text-sm font-bold ${cfg.text}`}>
                    {formatNumber(totalRows)}
                  </span>
                )}
              </CardHeader>

              {layersLoading && !data ? (
                <div className="flex items-center gap-2 text-xs text-[--text-muted]">
                  <Spinner size="sm" />
                  <span>Querying Trino…</span>
                </div>
              ) : !data ? (
                <p className="text-xs text-[--text-muted]">No data</p>
              ) : (
                <div className="space-y-2.5">
                  {data.tables.map((t) => {
                    const pct = t.error ? 0 : Math.max(((t.row_count ?? 0) / maxRows) * 100, t.row_count ? 2 : 0);
                    return (
                      <div key={t.table}>
                        <div className="mb-1 flex items-center justify-between">
                          <span className="truncate font-mono text-[11px] text-[--text-secondary]">{t.table}</span>
                          <span className={`ml-2 shrink-0 font-mono text-[11px] tabular-nums ${cfg.text}`}>
                            {t.error ? 'err' : formatNumber(t.row_count)}
                          </span>
                        </div>
                        <div className="h-1 w-full overflow-hidden rounded-full bg-[--bg-elevated]">
                          <div
                            className={`h-full rounded-full transition-all duration-700 ${cfg.bar}`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}
