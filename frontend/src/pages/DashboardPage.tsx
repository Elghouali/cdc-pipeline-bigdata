import { useEffect, useState } from 'react';
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer,
} from 'recharts';
import {
  FlaskConical, TrendingUp, ShoppingBag, Crown, Wallet,
} from 'lucide-react';
import { runQuery } from '@/lib/api';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { PageSpinner } from '@/components/ui/Spinner';
import { cn, formatCurrency, formatNumber } from '@/lib/utils';

// ── colour palette ────────────────────────────────────────────────────────────
const CYAN    = '#00e5ff';
const EMERALD = '#10ffaa';
const AMBER   = '#fbbf24';
const PURPLE  = '#a855f7';
const BLUE    = '#60a5fa';
const RED     = '#f43f5e';

const CHANNEL_COLORS: Record<string, string> = {
  web: CYAN, mobile: EMERALD, store: PURPLE, agent: AMBER,
};
const SEGMENT_COLORS: Record<string, string> = {
  Premium: CYAN, B2B: PURPLE, B2C: EMERALD, Standard: AMBER,
};
const PIE_COLORS = [CYAN, PURPLE, EMERALD, AMBER, BLUE, RED];

const TICK_MUTED = '#374869';
const TICK_LABEL = '#7b90c0';

// ── mock data ─────────────────────────────────────────────────────────────────
function buildMockTrend() {
  return Array.from({ length: 14 }, (_, i) => {
    const d = new Date(); d.setDate(d.getDate() - (13 - i));
    const gross = 80_000 + Math.random() * 60_000;
    return { date: d.toISOString().slice(0, 10), gross: Math.round(gross), net: Math.round(gross * 0.78) };
  });
}

const MOCK_CHANNELS  = [
  { channel: 'web', revenue: 420_000 }, { channel: 'mobile', revenue: 310_000 },
  { channel: 'store', revenue: 185_000 }, { channel: 'agent', revenue: 95_000 },
];
const MOCK_PAYMENTS  = [
  { name: 'Credit Card', value: 48 }, { name: 'Bank Transfer', value: 22 },
  { name: 'Cash', value: 18 }, { name: 'Mobile Money', value: 12 },
];
const MOCK_SEGMENTS  = [
  { segment: 'Premium', orders: 1_240, revenue: 310_000 },
  { segment: 'B2C',     orders: 3_800, revenue: 480_000 },
  { segment: 'B2B',     orders: 920,   revenue: 290_000 },
  { segment: 'Standard',orders: 2_100, revenue: 240_000 },
];
const MOCK_CATEGORIES = [
  { category: 'Electronics', revenue: 380_000 }, { category: 'Fashion',  revenue: 210_000 },
  { category: 'Home',        revenue: 165_000 }, { category: 'Food',     revenue: 140_000 },
  { category: 'Beauty',      revenue: 95_000  }, { category: 'Sports',   revenue: 80_000  },
];

// ── tooltip ───────────────────────────────────────────────────────────────────
function ChartTip({ active, payload, label }: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-white/[0.08] bg-[--bg-glass] px-3 py-2 text-xs backdrop-blur-xl shadow-[0_8px_32px_rgba(0,0,0,0.5)]">
      {label && <p className="mb-1 font-mono text-[10px] uppercase tracking-widest text-[--text-muted]">{label}</p>}
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color }} className="font-mono font-semibold">
          {p.name}: <span className="text-[--text-primary]">{p.value > 10_000 ? formatCurrency(p.value) : formatNumber(p.value)}</span>
        </p>
      ))}
    </div>
  );
}

// ── stat card ─────────────────────────────────────────────────────────────────
interface StatCardProps {
  label: string;
  value: string;
  sub?: string;
  blob: string;
  icon: React.ElementType;
  iconColor: string;
  iconBg: string;
}

function StatCard({ label, value, sub, blob, icon: Icon, iconColor, iconBg }: StatCardProps) {
  return (
    <Card variant="glass" className="relative overflow-hidden">
      <div className={cn('pointer-events-none absolute -right-8 -top-8 h-28 w-28 rounded-full blur-3xl opacity-25', blob)} />
      <div className="flex items-start justify-between">
        <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[--text-muted]">{label}</p>
        <div className={cn('flex h-7 w-7 items-center justify-center rounded-lg ring-1 ring-white/10', iconBg)}>
          <Icon className={cn('h-3.5 w-3.5', iconColor)} strokeWidth={2.5} />
        </div>
      </div>
      <p className="mt-3 font-mono text-3xl font-black tracking-tight gradient-text">{value}</p>
      {sub && <p className="mt-1 text-xs text-[--text-muted]">{sub}</p>}
    </Card>
  );
}

// ── main page ─────────────────────────────────────────────────────────────────
interface Dash {
  trend:      { date: string; gross: number; net: number }[];
  channels:   { channel: string; revenue: number }[];
  payments:   { name: string; value: number }[];
  segments:   { segment: string; orders: number; revenue: number }[];
  categories: { category: string; revenue: number }[];
}

export function DashboardPage() {
  const [dash, setDash] = useState<Dash | null>(null);
  const [loading, setLoading] = useState(true);
  const [isDemo, setIsDemo] = useState(false);

  useEffect(() => { void load(); }, []);

  async function load() {
    setLoading(true);
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15_000);
    try {
      const sig = controller.signal;
      const [tR, cR, pR, sR, catR] = await Promise.all([
        runQuery(`SELECT sale_date, SUM(gross_revenue) AS gross, SUM(net_revenue) AS net
                  FROM iceberg.analytics.gold_sales_facts
                  WHERE sale_date >= current_date - interval '14' day
                  GROUP BY sale_date ORDER BY sale_date`, sig),
        runQuery(`SELECT channel, SUM(gross_revenue) AS revenue
                  FROM iceberg.analytics.gold_sales_facts
                  GROUP BY channel ORDER BY revenue DESC`, sig),
        runQuery(`SELECT method AS name, SUM(transaction_count) AS value
                  FROM iceberg.analytics.gold_payments_summary
                  GROUP BY method ORDER BY value DESC`, sig),
        runQuery(`SELECT customer_segment AS segment, SUM(order_count) AS orders,
                         SUM(gross_revenue) AS revenue
                  FROM iceberg.analytics.gold_sales_facts
                  GROUP BY customer_segment`, sig),
        runQuery(`SELECT product_category AS category, SUM(gross_revenue) AS revenue
                  FROM iceberg.analytics.gold_sales_facts
                  GROUP BY product_category ORDER BY revenue DESC LIMIT 6`, sig),
      ]);
      clearTimeout(timeout);
      setDash({
        trend:      tR.map((r) => ({ date: String(r.sale_date), gross: Number(r.gross), net: Number(r.net) })),
        channels:   cR.map((r) => ({ channel: String(r.channel), revenue: Number(r.revenue) })),
        payments:   pR.map((r) => ({ name: String(r.name), value: Number(r.value) })),
        segments:   sR.map((r) => ({ segment: String(r.segment), orders: Number(r.orders), revenue: Number(r.revenue) })),
        categories: catR.map((r) => ({ category: String(r.category), revenue: Number(r.revenue) })),
      });
      setIsDemo(false);
    } catch {
      clearTimeout(timeout);
      setDash({ trend: buildMockTrend(), channels: MOCK_CHANNELS, payments: MOCK_PAYMENTS, segments: MOCK_SEGMENTS, categories: MOCK_CATEGORIES });
      setIsDemo(true);
    } finally {
      setLoading(false);
    }
  }

  if (loading) return <div className="p-8"><PageSpinner /></div>;
  if (!dash) return null;

  const totalRevenue = dash.channels.reduce((s, r) => s + r.revenue, 0);
  const totalOrders  = dash.segments.reduce((s, r) => s + r.orders, 0);
  const top          = dash.channels[0];
  const avgOrder     = totalOrders > 0 ? totalRevenue / totalOrders : 0;

  return (
    <div className="page-enter p-8">
      <div className="mb-7 flex items-end justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.25em] text-[--text-muted]">
            Gold layer · business metrics
          </p>
          <h1 className="mt-1 text-2xl font-black tracking-tight text-[--text-primary]">
            KPI <span className="gradient-text">Dashboard</span>
          </h1>
        </div>
        {isDemo && (
          <Badge variant="warning">
            <FlaskConical className="h-3 w-3" />
            Demo — Trino unavailable
          </Badge>
        )}
      </div>

      {/* Bento grid */}
      <div className="grid gap-4 lg:grid-cols-4">
        {/* KPI row */}
        <StatCard
          label="Gross Revenue"
          value={formatCurrency(totalRevenue)}
          sub="All channels · 30d"
          blob="bg-cyan-500/40"
          icon={TrendingUp}
          iconColor="text-cyan-300"
          iconBg="bg-cyan-500/15"
        />
        <StatCard
          label="Total Orders"
          value={formatNumber(totalOrders)}
          sub="Across all segments"
          blob="bg-emerald-500/40"
          icon={ShoppingBag}
          iconColor="text-emerald-300"
          iconBg="bg-emerald-500/15"
        />
        <StatCard
          label="Top Channel"
          value={top?.channel?.toUpperCase() ?? '—'}
          sub={top ? formatCurrency(top.revenue) : undefined}
          blob="bg-purple-500/40"
          icon={Crown}
          iconColor="text-purple-300"
          iconBg="bg-purple-500/15"
        />
        <StatCard
          label="Avg Order Value"
          value={avgOrder > 0 ? formatCurrency(avgOrder) : '—'}
          sub="Per transaction"
          blob="bg-amber-500/40"
          icon={Wallet}
          iconColor="text-amber-300"
          iconBg="bg-amber-500/15"
        />

        {/* Revenue Trend — full width */}
        <Card variant="gradient" className="lg:col-span-4">
          <CardHeader>
            <CardTitle>Revenue Trend · Last 14 Days</CardTitle>
            <div className="flex items-center gap-3 text-[10px] font-mono uppercase tracking-widest">
              <span className="flex items-center gap-1.5 text-cyan-300">
                <span className="h-2 w-2 rounded-full bg-cyan-400 shadow-[0_0_6px_currentColor]" />
                Gross
              </span>
              <span className="flex items-center gap-1.5 text-emerald-300">
                <span className="h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_6px_currentColor]" />
                Net
              </span>
            </div>
          </CardHeader>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={dash.trend} margin={{ top: 4, right: 12, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="gGross" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor={CYAN}    stopOpacity={0.35} />
                  <stop offset="95%" stopColor={CYAN}    stopOpacity={0}    />
                </linearGradient>
                <linearGradient id="gNet" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor={EMERALD} stopOpacity={0.3}  />
                  <stop offset="95%" stopColor={EMERALD} stopOpacity={0}    />
                </linearGradient>
              </defs>
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: TICK_MUTED }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fontSize: 10, fill: TICK_MUTED }} tickLine={false} axisLine={false}
                tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`} />
              <Tooltip content={<ChartTip />} cursor={{ stroke: 'rgba(255,255,255,0.06)', strokeWidth: 1 }} />
              <Area type="monotone" dataKey="gross" name="Gross" stroke={CYAN}    fill="url(#gGross)" strokeWidth={2.5} dot={false} />
              <Area type="monotone" dataKey="net"   name="Net"   stroke={EMERALD} fill="url(#gNet)"   strokeWidth={2.5} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </Card>

        {/* Channels */}
        <Card variant="glass" className="lg:col-span-2">
          <CardHeader><CardTitle>Revenue by Channel</CardTitle></CardHeader>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={dash.channels} layout="vertical" margin={{ left: 0, right: 12 }}>
              <XAxis type="number" tick={{ fontSize: 10, fill: TICK_MUTED }} tickLine={false} axisLine={false}
                tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`} />
              <YAxis type="category" dataKey="channel" tick={{ fontSize: 11, fill: TICK_LABEL, fontFamily: 'JetBrains Mono' }} width={64} tickLine={false} axisLine={false} />
              <Tooltip content={<ChartTip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
              <Bar dataKey="revenue" name="Revenue" radius={[0, 6, 6, 0]}>
                {dash.channels.map((e) => <Cell key={e.channel} fill={CHANNEL_COLORS[e.channel] ?? BLUE} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>

        {/* Payment Mix */}
        <Card variant="glass" className="lg:col-span-2">
          <CardHeader><CardTitle>Payment Mix</CardTitle></CardHeader>
          <div className="flex items-center gap-5">
            <ResponsiveContainer width={160} height={160}>
              <PieChart>
                <Pie data={dash.payments} dataKey="value" nameKey="name" cx="50%" cy="50%"
                  innerRadius={44} outerRadius={68} strokeWidth={0} paddingAngle={2}>
                  {dash.payments.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                </Pie>
                <Tooltip content={<ChartTip />} />
              </PieChart>
            </ResponsiveContainer>
            <ul className="flex-1 space-y-2">
              {dash.payments.map((p, i) => (
                <li key={p.name} className="flex items-center justify-between text-xs">
                  <span className="flex items-center gap-2 text-[--text-secondary]">
                    <span className="h-2.5 w-2.5 rounded-sm shadow-[0_0_6px_currentColor]" style={{ background: PIE_COLORS[i % PIE_COLORS.length], color: PIE_COLORS[i % PIE_COLORS.length] }} />
                    {p.name}
                  </span>
                  <span className="font-mono text-sm font-bold text-[--text-primary]">{p.value}<span className="text-xs text-[--text-muted]">%</span></span>
                </li>
              ))}
            </ul>
          </div>
        </Card>

        {/* Segments — span 3 */}
        <Card variant="glass" className="lg:col-span-3">
          <CardHeader><CardTitle>Segment Performance</CardTitle></CardHeader>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={dash.segments} margin={{ top: 4, right: 12, bottom: 0, left: 0 }}>
              <XAxis dataKey="segment" tick={{ fontSize: 11, fill: TICK_LABEL }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fontSize: 10, fill: TICK_MUTED }} tickLine={false} axisLine={false}
                tickFormatter={(v: number) => formatNumber(v)} />
              <Tooltip content={<ChartTip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
              <Bar dataKey="orders" name="Orders" radius={[6, 6, 0, 0]}>
                {dash.segments.map((s) => <Cell key={s.segment} fill={SEGMENT_COLORS[s.segment] ?? BLUE} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>

        {/* Categories */}
        <Card variant="glass" className="lg:col-span-1">
          <CardHeader><CardTitle>Top Categories</CardTitle></CardHeader>
          <ul className="space-y-2.5">
            {dash.categories.map((c, i) => {
              const max = Math.max(...dash.categories.map(x => x.revenue));
              const pct = (c.revenue / max) * 100;
              return (
                <li key={c.category}>
                  <div className="mb-1 flex items-center justify-between text-xs">
                    <span className="flex items-center gap-1.5">
                      <span className="font-mono text-[10px] text-[--text-muted]">{String(i + 1).padStart(2, '0')}</span>
                      <span className="text-[--text-primary]">{c.category}</span>
                    </span>
                    <span className="font-mono font-semibold text-[--text-secondary]">{formatCurrency(c.revenue)}</span>
                  </div>
                  <div className="h-1 w-full overflow-hidden rounded-full bg-white/[0.04]">
                    <div className="h-full rounded-full bg-gradient-to-r from-purple-500 to-cyan-400" style={{ width: `${pct}%` }} />
                  </div>
                </li>
              );
            })}
          </ul>
        </Card>
      </div>
    </div>
  );
}
