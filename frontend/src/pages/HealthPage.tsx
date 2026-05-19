import { useEffect, useState } from 'react';
import { CheckCircle2, Clock, RefreshCw, XCircle } from 'lucide-react';
import { fetchHealth } from '@/lib/api';
import type { HealthItem } from '@/types/api';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { PageSpinner } from '@/components/ui/Spinner';
import { formatLatency, formatRelativeTime } from '@/lib/utils';

const SERVICE_LABELS: Record<string, string> = {
  postgres:        'PostgreSQL',
  trino:           'Trino',
  'kafka-connect': 'Kafka Connect',
  'spark-master':  'Spark Master',
  minio:           'MinIO',
};

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
            <div className="text-right">
              <span
                className={`font-mono text-2xl font-bold ${
                  upCount === items.length ? 'text-emerald-400' : 'text-amber-400'
                }`}
              >
                {upCount}/{items.length}
              </span>
              <p className="text-[10px] text-[--text-muted]">services up</p>
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

      {loading && <PageSpinner />}

      {!loading && error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {!loading && !error && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((item) => (
            <ServiceCard key={item.service} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}

function ServiceCard({ item }: { item: HealthItem }) {
  const isUp = item.status === 'up';
  const label = SERVICE_LABELS[item.service] ?? item.service;

  return (
    <Card
      glow={isUp ? 'emerald' : 'none'}
      className="transition-shadow hover:border-[--border-focus]"
    >
      <CardHeader>
        <CardTitle>{label}</CardTitle>
        <Badge variant={isUp ? 'success' : 'error'}>
          {isUp ? <CheckCircle2 className="h-3 w-3" /> : <XCircle className="h-3 w-3" />}
          {isUp ? 'UP' : 'DOWN'}
        </Badge>
      </CardHeader>

      <div className="space-y-2">
        <div className="flex items-center gap-2 text-xs text-[--text-muted]">
          <Clock className="h-3.5 w-3.5" />
          <span>Latency:</span>
          <span className="font-mono text-[--text-secondary]">{formatLatency(item.latency_ms)}</span>
        </div>

        {item.detail && (
          <p className="rounded bg-[--bg-elevated] px-2 py-1 font-mono text-xs leading-snug text-red-400">
            {item.detail}
          </p>
        )}

        <div className={`h-1 rounded-full ${isUp ? 'bg-emerald-500/40' : 'bg-red-500/40'}`} />
      </div>
    </Card>
  );
}
