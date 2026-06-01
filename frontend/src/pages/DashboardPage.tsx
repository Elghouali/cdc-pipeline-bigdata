import { useEffect, useRef, useState } from 'react';
import { TrendingDown, TrendingUp, Minus, RefreshCw } from 'lucide-react';
import { AreaChart, Area, ResponsiveContainer } from 'recharts';
import { fetchHealth, fetchMetrics } from '@/lib/api';
import type { HealthItem, Layer, MetricsResponse } from '@/types/api';
import { cn, formatNumber } from '@/lib/utils';
import { Badge } from '@/components/ui/Badge';

// ── Count-up hook ─────────────────────────────────────────────────────────────
function useCountUp(target: number, duration = 900): number {
  const [val, setVal] = useState(0);
  const frameRef = useRef<number>(0);
  useEffect(() => {
    cancelAnimationFrame(frameRef.current);
    if (target === 0) { setVal(0); return; }
    const start = performance.now();
    const from = val;
    const animate = (now: number) => {
      const p = Math.min((now - start) / duration, 1);
      const ease = 1 - Math.pow(1 - p, 3);
      setVal(Math.round(from + (target - from) * ease));
      if (p < 1) frameRef.current = requestAnimationFrame(animate);
    };
    frameRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frameRef.current);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target, duration]);
  return val;
}

// ── Mock KPI data ─────────────────────────────────────────────────────────────
const KPI_METRICS = [
  { key: 'revenue',   label: 'Total Revenue',   value: 2847392, unit: 'MAD', delta: 12.4, trend: 'up'   as const },
  { key: 'orders',    label: 'Orders Today',     value: 1847,    unit: '',    delta: 8.1,  trend: 'up'   as const },
  { key: 'customers', label: 'Active Customers', value: 12483,   unit: '',    delta: 0,    trend: 'flat' as const },
  { key: 'returns',   label: 'Returns',          value: 234,     unit: '',    delta: -3.2, trend: 'down' as const },
];

function buildSparkData(base: number, n = 12): { v: number }[] {
  const pts: { v: number }[] = [];
  let v = base * 0.5;
  for (let i = 0; i < n - 1; i++) {
    v = Math.max(0, v + (Math.random() - 0.35) * base * 0.1);
    pts.push({ v: Math.round(v) });
  }
  pts.push({ v: base });
  return pts;
}

// ── Live event feed ───────────────────────────────────────────────────────────
type OpType = 'INSERT' | 'UPDATE' | 'DELETE';
interface FeedEvent { id: number; ts: string; op: OpType; table: string; payload: string; }

const TABLES = ['orders', 'customers', 'payments', 'returns', 'products'];
const NAMES  = ['Karim B.', 'Fatima Z.', 'Youssef E.', 'Amina L.', 'Hassan M.', 'Sara A.', 'Omar R.'];
const OPS: OpType[] = ['INSERT', 'INSERT', 'INSERT', 'UPDATE', 'UPDATE', 'DELETE'];

function makeEvent(id: number): FeedEvent {
  const op = OPS[Math.floor(Math.random() * OPS.length)];
  const table = TABLES[Math.floor(Math.random() * TABLES.length)];
  const name = NAMES[Math.floor(Math.random() * NAMES.length)];
  const amount = (Math.random() * 1200 + 50).toFixed(2);
  const now = new Date();
  const ts = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}:${String(now.getSeconds()).padStart(2,'0')}.${String(now.getMilliseconds()).padStart(3,'0')}`;
  const payload =
    op === 'DELETE' ? `id:${1000 + id} processed` :
    table === 'orders' ? `${name} · ${amount} MAD` :
    table === 'customers' ? `${name} · email updated` :
    `id:${1000 + id} · ${amount} MAD`;
  return { id, ts, op, table, payload };
}

const OP_STYLE: Record<OpType, { badge: 'success' | 'warning' | 'error'; dotColor: string }> = {
  INSERT: { badge: 'success', dotColor: 'var(--accent-green)'  },
  UPDATE: { badge: 'warning', dotColor: 'var(--accent-yellow)' },
  DELETE: { badge: 'error',   dotColor: 'var(--accent-red)'    },
};

// ── Service health nodes ──────────────────────────────────────────────────────
const SERVICE_META: Record<string, { label: string; metric: string; color: string }> = {
  postgres:        { label: 'PostgreSQL',    metric: 'WAL replication', color: '#2563EB' },
  'kafka-connect': { label: 'Kafka Connect', metric: 'Debezium CDC',    color: '#EA580C' },
  'spark-master':  { label: 'Spark Master',  metric: '2 active jobs',   color: '#CA8A04' },
  minio:           { label: 'MinIO',         metric: 'S3 API',          color: '#16A34A' },
  trino:           { label: 'Trino',         metric: 'Distributed SQL', color: '#7C3AED' },
};

// ── KPI Tile ──────────────────────────────────────────────────────────────────
function KpiTile({ label, value, unit, delta, trend, sparkData }: {
  label: string; value: number; unit: string; delta: number;
  trend: 'up' | 'down' | 'flat'; sparkData: { v: number }[];
}) {
  const displayed = useCountUp(value);
  const formatted = unit === 'MAD'
    ? `${(displayed / 1_000_000).toFixed(2)}M`
    : formatNumber(displayed);

  const trendColor = trend === 'up' ? 'var(--accent-green)' : trend === 'down' ? 'var(--accent-red)' : 'var(--text-dim)';
  const sparkColor = trend === 'down' ? 'var(--accent-red)' : 'var(--accent)';

  return (
    <div className="rounded-xl border border-[--border] bg-[--bg-surface] p-5 shadow-[var(--shadow-sm)] transition-shadow hover:shadow-[var(--shadow-md)]">
      <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-[--text-dim]">{label}</p>
      <div className="flex items-end justify-between gap-3">
        <div>
          <p className="font-mono text-[28px] font-light leading-none tracking-tight text-[--text-primary]">
            {unit === 'MAD' && <span className="mr-1 text-sm font-normal text-[--text-muted]">MAD</span>}
            {formatted}
          </p>
          <div className="mt-2 flex items-center gap-1.5">
            {trend === 'up'   && <TrendingUp   className="h-3.5 w-3.5" style={{ color: trendColor }} />}
            {trend === 'down' && <TrendingDown  className="h-3.5 w-3.5" style={{ color: trendColor }} />}
            {trend === 'flat' && <Minus         className="h-3.5 w-3.5" style={{ color: trendColor }} />}
            <span className="font-mono text-[11px]" style={{ color: trendColor }}>
              {trend === 'flat' ? 'stable' : `${delta > 0 ? '+' : ''}${delta}% today`}
            </span>
          </div>
        </div>
        <div className="h-10 w-16 shrink-0 opacity-60">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={sparkData} margin={{ top: 2, right: 0, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id={`sg-${label}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={sparkColor} stopOpacity={0.3} />
                  <stop offset="100%" stopColor={sparkColor} stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area
                type="monotone"
                dataKey="v"
                stroke={sparkColor}
                strokeWidth={1.5}
                fill={`url(#sg-${label})`}
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

// ── Layer card ────────────────────────────────────────────────────────────────
const LAYER_CFG = {
  bronze: { label: 'Bronze', color: '#F59E0B', bg: 'rgba(245,158,11,0.07)',  border: 'rgba(245,158,11,0.18)', badgeVariant: 'bronze' as const },
  silver: { label: 'Silver', color: '#9CA3AF', bg: 'rgba(156,163,175,0.06)', border: 'rgba(156,163,175,0.15)', badgeVariant: 'muted'  as const },
  gold:   { label: 'Gold',   color: '#FCD34D', bg: 'rgba(252,211,77,0.07)',  border: 'rgba(252,211,77,0.18)', badgeVariant: 'warning' as const },
};

function LayerCard({ layer, data }: { layer: Layer; data: MetricsResponse | undefined }) {
  const cfg = LAYER_CFG[layer];
  const total = data?.tables.reduce((s, t) => s + (t.row_count ?? 0), 0) ?? 0;
  const displayed = useCountUp(total);

  return (
    <div
      className="rounded-xl border p-5 transition-shadow hover:shadow-[var(--shadow-sm)]"
      style={{ backgroundColor: cfg.bg, borderColor: cfg.border }}
    >
      <div className="mb-3 flex items-center justify-between">
        <span className="text-[11px] font-semibold uppercase tracking-widest" style={{ color: cfg.color }}>
          {cfg.label}
        </span>
        {data && <Badge variant={cfg.badgeVariant}>{data.tables.length} tables</Badge>}
      </div>
      {data ? (
        <>
          <p className="font-mono text-2xl font-light text-[--text-primary]">{formatNumber(displayed)}</p>
          <p className="mt-0.5 text-[11px] text-[--text-dim]">rows total</p>
          <div className="mt-4 space-y-2">
            {data.tables.slice(0, 3).map(t => {
              const pct = total > 0 ? ((t.row_count ?? 0) / total) * 100 : 0;
              return (
                <div key={t.table}>
                  <div className="mb-1 flex items-center justify-between">
                    <span className="truncate font-mono text-[10px] text-[--text-muted]">{t.table}</span>
                    <span className="ml-2 shrink-0 font-mono text-[10px] font-medium" style={{ color: cfg.color }}>
                      {formatNumber(t.row_count)}
                    </span>
                  </div>
                  <div className="h-1 w-full rounded-full bg-[--border]">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{ width: `${pct}%`, backgroundColor: cfg.color, opacity: 0.7 }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </>
      ) : (
        <div className="space-y-2 pt-1">
          {[60, 40, 80].map(w => (
            <div key={w} className="skeleton-shimmer h-3 rounded" style={{ width: `${w}%` }} />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export function DashboardPage() {
  const [health, setHealth] = useState<HealthItem[]>([]);
  const [layers, setLayers] = useState<Partial<Record<Layer, MetricsResponse>>>({});
  const [events, setEvents] = useState<FeedEvent[]>(() =>
    Array.from({ length: 8 }, (_, i) => makeEvent(i))
  );
  const [refreshing, setRefreshing] = useState(false);
  const eventIdRef = useRef(100);
  const sparkData = useRef(KPI_METRICS.map(m => buildSparkData(m.value)));

  async function loadData(manual = false) {
    if (manual) setRefreshing(true);
    fetchHealth().then(setHealth).catch(() => {});
    try {
      const layerResults = await Promise.allSettled([
        fetchMetrics('bronze'),
        fetchMetrics('silver'),
        fetchMetrics('gold'),
      ]);
      const layerKeys: Layer[] = ['bronze', 'silver', 'gold'];
      setLayers(prev => {
        const next = { ...prev };
        layerResults.forEach((r, i) => {
          if (r.status === 'fulfilled') {
            next[layerKeys[i]] = r.value;
          } else {
            next[layerKeys[i]] = { layer: layerKeys[i], tables: [], cached: false, generated_at: new Date().toISOString() };
          }
        });
        return next;
      });
    } catch { /* keep previous */ }
    if (manual) setRefreshing(false);
  }

  useEffect(() => {
    void loadData();
    const id = setInterval(() => void loadData(), 30_000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const id = setInterval(() => {
      const newEv = makeEvent(eventIdRef.current++);
      setEvents(prev => [newEv, ...prev.slice(0, 19)]);
    }, 2200 + Math.random() * 1400);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="page-enter p-6 space-y-6">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-[--text-dim]">Dashboard</p>
          <h1 className="mt-0.5 text-xl font-semibold text-[--text-primary]">KPI Overview</h1>
        </div>
        <button
          onClick={() => void loadData(true)}
          disabled={refreshing}
          className="flex items-center gap-2 rounded-lg border border-[--border] bg-[--bg-surface] px-3.5 py-2 text-[12px] font-medium text-[--text-muted] shadow-[var(--shadow-sm)] transition-all hover:bg-[--bg-elevated] hover:text-[--text-primary] disabled:opacity-50"
        >
          <RefreshCw className={cn('h-3.5 w-3.5', refreshing && 'animate-spin')} />
          Refresh
        </button>
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {KPI_METRICS.map((m, i) => (
          <KpiTile
            key={m.key}
            label={m.label}
            value={m.value}
            unit={m.unit}
            delta={m.delta}
            trend={m.trend}
            sparkData={sparkData.current[i]}
          />
        ))}
      </div>

      {/* Main bento grid */}
      <div className="grid grid-cols-12 gap-4">

        {/* Medallion Layers */}
        <div className="col-span-12 lg:col-span-3 space-y-3">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-[--text-dim]">Medallion Layers</p>
          {(['bronze', 'silver', 'gold'] as Layer[]).map(l => (
            <LayerCard key={l} layer={l} data={layers[l]} />
          ))}
        </div>

        {/* Event feed */}
        <div className="col-span-12 lg:col-span-9">
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <p className="text-[11px] font-semibold uppercase tracking-widest text-[--text-dim]">Kafka Events</p>
              <span className="flex items-center gap-1.5 rounded-full border border-[--accent-green]/20 bg-[--accent-green]/10 px-2 py-0.5">
                <span className="h-1.5 w-1.5 rounded-full bg-[--accent-green] node-glow" />
                <span className="font-mono text-[9px] font-semibold text-[--accent-green]">LIVE</span>
              </span>
            </div>
            <span className="font-mono text-[11px] text-[--text-dim]">{events.length} events</span>
          </div>

          <div className="rounded-xl border border-[--border] bg-[--bg-surface] overflow-hidden shadow-[var(--shadow-sm)]">
            {/* Table header */}
            <div className="grid grid-cols-[120px_70px_140px_1fr] border-b border-[--border] bg-[--bg-elevated] px-4 py-2.5">
              {['Time', 'Op', 'Table', 'Payload'].map(h => (
                <span key={h} className="text-[10px] font-semibold uppercase tracking-widest text-[--text-dim]">{h}</span>
              ))}
            </div>
            <div className="max-h-[400px] overflow-y-auto">
              {events.map((ev, idx) => {
                const s = OP_STYLE[ev.op];
                return (
                  <div
                    key={ev.id}
                    className={cn(
                      'grid grid-cols-[120px_70px_140px_1fr] items-center border-b border-[--border-subtle] px-4 py-2.5 transition-colors hover:bg-[--bg-elevated] last:border-0',
                      idx === 0 && 'event-enter'
                    )}
                  >
                    <span className="font-mono text-[11px] text-[--text-dim]">{ev.ts}</span>
                    <div><Badge variant={s.badge}>{ev.op}</Badge></div>
                    <span className="font-mono text-[11px] text-[--text-muted]">{ev.table}</span>
                    <span className="truncate font-mono text-[11px] text-[--text-dim]">{ev.payload}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Service health grid */}
      <div>
        <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-[--text-dim]">Service Health</p>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {Object.entries(SERVICE_META).map(([key, meta]) => {
            const item = health.find(h => h.service === key);
            const isUp = item?.status === 'up';
            const known = !!item;
            const dotColor = !known ? 'var(--text-dim)' : isUp ? 'var(--accent-green)' : 'var(--accent-red)';

            return (
              <div
                key={key}
                className="rounded-xl border border-[--border] bg-[--bg-surface] p-4 shadow-[var(--shadow-sm)] transition-shadow hover:shadow-[var(--shadow-md)]"
              >
                <div className="mb-3 flex items-center justify-between">
                  <span className="text-[12px] font-semibold text-[--text-primary]">{meta.label}</span>
                  <span
                    className="h-2 w-2 rounded-full transition-colors"
                    style={{ backgroundColor: dotColor }}
                  />
                </div>
                <p className="text-[11px] text-[--text-muted]">{meta.metric}</p>
                {item?.latency_ms != null && (
                  <p className={cn(
                    'mt-2 font-mono text-lg font-light',
                    item.latency_ms < 100 ? 'text-[--accent-green]' :
                    item.latency_ms < 300 ? 'text-[--accent-yellow]' : 'text-[--accent-red]'
                  )}>
                    {item.latency_ms}
                    <span className="ml-0.5 text-[10px] text-[--text-dim]">ms</span>
                  </p>
                )}
                {!item && (
                  <p className="mt-2 font-mono text-sm text-[--text-dim]">—</p>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
