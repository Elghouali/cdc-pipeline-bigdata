import { useEffect, useState } from 'react';
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer,
} from 'recharts';
import { FlaskConical } from 'lucide-react';
import { runQuery } from '@/lib/api';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { PageSpinner } from '@/components/ui/Spinner';
import { formatCurrency, formatNumber } from '@/lib/utils';

// ── colour palette ────────────────────────────────────────────────────────────
const CYAN    = '#00d4ff';
const EMERALD = '#00ff88';
const AMBER   = '#ffb800';
const PURPLE  = '#a78bfa';
const BLUE    = '#60a5fa';
const RED     = '#ff4b4b';

const CHANNEL_COLORS: Record<string, string> = {
  web: CYAN, mobile: EMERALD, store: PURPLE, agent: AMBER,
};
const SEGMENT_COLORS: Record<string, string> = {
  Premium: CYAN, B2B: PURPLE, B2C: EMERALD, Standard: AMBER,
};
const PIE_COLORS = [CYAN, EMERALD, AMBER, PURPLE, BLUE, RED];

// ── mock data (fallback when Trino is unavailable) ────────────────────────────
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
    <div className="rounded-md border border-[--border] bg-[--bg-elevated] px-3 py-2 text-xs shadow-lg">
      {label && <p className="mb-1 font-medium text-[--text-muted]">{label}</p>}
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color }}>
          {p.name}: {p.value > 10_000 ? formatCurrency(p.value) : formatNumber(p.value)}
        </p>
      ))}
    </div>
  );
}

// ── stat card ─────────────────────────────────────────────────────────────────
function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <Card className="flex flex-col gap-1">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-[--text-muted]">{label}</p>
      <p className="font-mono text-2xl font-bold text-[--accent-cyan]">{value}</p>
      {sub && <p className="text-[11px] text-[--text-muted]">{sub}</p>}
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

  if (loading) return <div className="p-6"><PageSpinner /></div>;
  if (!dash) return null;

  const totalRevenue = dash.channels.reduce((s, r) => s + r.revenue, 0);
  const totalOrders  = dash.segments.reduce((s, r) => s + r.orders, 0);
  const top          = dash.channels[0];

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-[--text-primary]">KPI Dashboard</h1>
          <p className="text-xs text-[--text-muted]">Business metrics · Gold layer</p>
        </div>
        {isDemo && (
          <Badge variant="warning">
            <FlaskConical className="h-3 w-3" />
            Demo data — Trino unavailable
          </Badge>
        )}
      </div>

      {/* KPI stats */}
      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Stat label="Gross Revenue (30d)" value={formatCurrency(totalRevenue)} />
        <Stat label="Total Orders" value={formatNumber(totalOrders)} />
        <Stat label="Top Channel" value={top?.channel ?? '—'} sub={top ? formatCurrency(top.revenue) : undefined} />
        <Stat label="Avg Order Value" value={totalOrders > 0 ? formatCurrency(totalRevenue / totalOrders) : '—'} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Revenue Trend */}
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle>Revenue Trend — Last 14 Days</CardTitle></CardHeader>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={dash.trend} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="gGross" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor={CYAN}    stopOpacity={0.25} />
                  <stop offset="95%" stopColor={CYAN}    stopOpacity={0}    />
                </linearGradient>
                <linearGradient id="gNet" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor={EMERALD} stopOpacity={0.25} />
                  <stop offset="95%" stopColor={EMERALD} stopOpacity={0}    />
                </linearGradient>
              </defs>
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#4a5a7a' }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fontSize: 10, fill: '#4a5a7a' }} tickLine={false} axisLine={false}
                tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`} />
              <Tooltip content={<ChartTip />} />
              <Area type="monotone" dataKey="gross" name="Gross" stroke={CYAN}    fill="url(#gGross)" strokeWidth={2} dot={false} />
              <Area type="monotone" dataKey="net"   name="Net"   stroke={EMERALD} fill="url(#gNet)"   strokeWidth={2} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </Card>

        {/* Revenue by Channel */}
        <Card>
          <CardHeader><CardTitle>Revenue by Channel</CardTitle></CardHeader>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={dash.channels} layout="vertical" margin={{ left: 0, right: 8 }}>
              <XAxis type="number" tick={{ fontSize: 10, fill: '#4a5a7a' }} tickLine={false} axisLine={false}
                tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`} />
              <YAxis type="category" dataKey="channel" tick={{ fontSize: 10, fill: '#8b9fc4' }} width={52} tickLine={false} axisLine={false} />
              <Tooltip content={<ChartTip />} />
              <Bar dataKey="revenue" name="Revenue" radius={[0, 4, 4, 0]}>
                {dash.channels.map((e) => <Cell key={e.channel} fill={CHANNEL_COLORS[e.channel] ?? BLUE} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>

        {/* Payment Mix */}
        <Card>
          <CardHeader><CardTitle>Payment Mix</CardTitle></CardHeader>
          <div className="flex items-center gap-4">
            <ResponsiveContainer width={140} height={140}>
              <PieChart>
                <Pie data={dash.payments} dataKey="value" nameKey="name" cx="50%" cy="50%"
                  innerRadius={38} outerRadius={60} strokeWidth={0}>
                  {dash.payments.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                </Pie>
                <Tooltip content={<ChartTip />} />
              </PieChart>
            </ResponsiveContainer>
            <ul className="flex-1 space-y-1.5">
              {dash.payments.map((p, i) => (
                <li key={p.name} className="flex items-center justify-between text-xs">
                  <span className="flex items-center gap-1.5 text-[--text-secondary]">
                    <span className="h-2 w-2 rounded-full" style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
                    {p.name}
                  </span>
                  <span className="font-mono text-[--text-primary]">{p.value}%</span>
                </li>
              ))}
            </ul>
          </div>
        </Card>

        {/* Segment Performance */}
        <Card>
          <CardHeader><CardTitle>Segment Performance</CardTitle></CardHeader>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={dash.segments} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <XAxis dataKey="segment" tick={{ fontSize: 10, fill: '#8b9fc4' }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fontSize: 10, fill: '#4a5a7a' }} tickLine={false} axisLine={false}
                tickFormatter={(v: number) => formatNumber(v)} />
              <Tooltip content={<ChartTip />} />
              <Bar dataKey="orders" name="Orders" radius={[4, 4, 0, 0]}>
                {dash.segments.map((s) => <Cell key={s.segment} fill={SEGMENT_COLORS[s.segment] ?? BLUE} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>

        {/* Top Categories */}
        <Card>
          <CardHeader><CardTitle>Top Categories by Revenue</CardTitle></CardHeader>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={dash.categories} layout="vertical" margin={{ left: 0, right: 8 }}>
              <XAxis type="number" tick={{ fontSize: 10, fill: '#4a5a7a' }} tickLine={false} axisLine={false}
                tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`} />
              <YAxis type="category" dataKey="category" tick={{ fontSize: 10, fill: '#8b9fc4' }} width={72} tickLine={false} axisLine={false} />
              <Tooltip content={<ChartTip />} />
              <Bar dataKey="revenue" name="Revenue" fill={PURPLE} radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>
    </div>
  );
}
