import { useEffect, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { fetchHealth } from '@/lib/api';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { PageSpinner } from '@/components/ui/Spinner';

interface SparkJob {
  id: string;
  name: string;
  status: 'running' | 'succeeded' | 'failed';
  startedAgo: string;
  duration: string;
}

const DEMO_JOBS: SparkJob[] = [
  { id: '1', name: 'cdc-bronze-ingestion',  status: 'running',   startedAgo: '2 min ago',  duration: '2m 14s' },
  { id: '2', name: 'cdc-silver-dedup',       status: 'succeeded', startedAgo: '7 min ago',  duration: '1m 42s' },
  { id: '3', name: 'cdc-gold-aggregation',   status: 'succeeded', startedAgo: '12 min ago', duration: '3m 05s' },
  { id: '4', name: 'cdc-bronze-ingestion',   status: 'succeeded', startedAgo: '17 min ago', duration: '2m 08s' },
  { id: '5', name: 'cdc-silver-dedup',       status: 'failed',    startedAgo: '22 min ago', duration: '0m 31s' },
];

function statusBadge(s: SparkJob['status']) {
  if (s === 'running')   return <Badge variant="info">Running</Badge>;
  if (s === 'succeeded') return <Badge variant="success">Succeeded</Badge>;
  return <Badge variant="error">Failed</Badge>;
}

export function StatsPage() {
  const [loading, setLoading] = useState(true);
  const [sparkUp, setSparkUp] = useState<boolean | null>(null);

  useEffect(() => {
    fetchHealth()
      .then((items) => {
        const master = items.find((i) => i.service === 'spark-master');
        setSparkUp(master?.status === 'up' ?? false);
      })
      .catch(() => setSparkUp(false))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-[--text-primary]">Spark Jobs</h1>
          <p className="text-xs text-[--text-muted]">Recent Spark Structured Streaming batches</p>
        </div>
        <button
          title="Refresh"
          onClick={() => window.location.reload()}
          className="rounded-md p-2 text-[--text-muted] transition-colors hover:bg-[--bg-elevated] hover:text-[--text-primary]"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>

      {loading && <PageSpinner />}

      {!loading && sparkUp === false && (
        <div className="mb-4 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-400">
          Spark Master not reachable — showing demo data. Run{' '}
          <code className="font-mono">make up</code> to start the stack.
        </div>
      )}

      {!loading && (
        <Card className="overflow-hidden p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[--border] bg-[--bg-elevated]">
                {['Job Name', 'Status', 'Started', 'Duration'].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[--text-muted]">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {DEMO_JOBS.map((job, i) => (
                <tr
                  key={job.id}
                  className={`border-b border-[--border] last:border-0 ${i % 2 === 1 ? 'bg-[--bg-elevated]/40' : ''}`}
                >
                  <td className="px-4 py-3 font-mono text-xs text-[--text-primary]">{job.name}</td>
                  <td className="px-4 py-3">{statusBadge(job.status)}</td>
                  <td className="px-4 py-3 text-xs text-[--text-muted]">{job.startedAgo}</td>
                  <td className="px-4 py-3 font-mono text-xs text-[--text-secondary]">{job.duration}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}
