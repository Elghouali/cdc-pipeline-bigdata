import { NavLink } from 'react-router-dom';
import { Activity, Code2, Database, LayoutDashboard, LogOut, Radio, Workflow } from 'lucide-react';
import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/context/AuthContext';
import { fetchHealth } from '@/lib/api';
import type { HealthItem } from '@/types/api';

interface PipelineNode {
  id: string;
  label: string;
  sublabel: string;
  port: string;
  serviceKey: string | null;
  color: string;
}

const PIPELINE: PipelineNode[] = [
  { id: 'postgres', label: 'PostgreSQL',    sublabel: 'WAL source',      port: '5432', serviceKey: 'postgres',      color: '#58A6FF' },
  { id: 'debezium', label: 'Debezium',      sublabel: 'CDC connector',   port: '8083', serviceKey: 'kafka-connect', color: '#F85149' },
  { id: 'kafka',    label: 'Kafka',         sublabel: 'Event stream',    port: '9092', serviceKey: null,            color: '#FFA657' },
  { id: 'spark',    label: 'Spark',         sublabel: 'Stream proc.',    port: '7077', serviceKey: 'spark-master',  color: '#D29922' },
  { id: 'minio',    label: 'MinIO',         sublabel: 'Object store',    port: '9000', serviceKey: 'minio',         color: '#3FB950' },
  { id: 'iceberg',  label: 'Iceberg',       sublabel: 'Table format',    port: '—',    serviceKey: null,            color: '#79C0FF' },
  { id: 'trino',    label: 'Trino',         sublabel: 'Distributed SQL', port: '8080', serviceKey: 'trino',         color: '#BC8CFF' },
];

const NAV = [
  { to: '/health',    icon: Activity,        label: 'Pipeline Health' },
  { to: '/dashboard', icon: LayoutDashboard, label: 'Overview'        },
  { to: '/metrics',   icon: Database,        label: 'Data Layers'     },
  { to: '/stats',     icon: Radio,           label: 'Event Stream'    },
  { to: '/query',     icon: Code2,           label: 'Query Console'   },
];

export function Sidebar() {
  const { username, logout } = useAuth();
  const [healthMap, setHealthMap] = useState<Record<string, HealthItem>>({});
  const [uptimeStart] = useState(() => Date.now());
  const [uptimeDisplay, setUptimeDisplay] = useState('0m');

  useEffect(() => {
    async function poll() {
      try {
        const items = await fetchHealth();
        setHealthMap(Object.fromEntries(items.map(i => [i.service, i])));
      } catch { /* silent */ }
    }
    void poll();
    const id = setInterval(poll, 30_000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const id = setInterval(() => {
      const s = Math.floor((Date.now() - uptimeStart) / 1000);
      const d = Math.floor(s / 86400);
      const h = Math.floor((s % 86400) / 3600);
      const m = Math.floor((s % 3600) / 60);
      if (d > 0) setUptimeDisplay(`${d}d ${h}h ${m}m`);
      else if (h > 0) setUptimeDisplay(`${h}h ${m}m`);
      else setUptimeDisplay(`${m}m`);
    }, 30_000);
    return () => clearInterval(id);
  }, [uptimeStart]);

  return (
    <aside className="relative flex h-screen w-60 shrink-0 flex-col border-r border-[--border] bg-[--bg-surface]">

      {/* Brand */}
      <div className="flex h-14 items-center gap-3 border-b border-[--border] px-4">
        <div className="flex h-7 w-7 items-center justify-center rounded bg-[--bg-elevated] border border-[--border]">
          <Workflow className="h-3.5 w-3.5 text-[--accent-cyan]" strokeWidth={2.5} />
        </div>
        <div>
          <p className="text-sm font-semibold text-[--text-primary] leading-none">CDC Pipeline</p>
          <p className="mt-0.5 font-mono text-[9px] uppercase tracking-[0.12em] text-[--text-dim]">Medallion Console</p>
        </div>
      </div>

      {/* Scrollable content */}
      <div className="flex flex-1 flex-col overflow-y-auto overflow-x-hidden">

        {/* Pipeline topology */}
        <div className="px-4 pt-4 pb-2">
          <p className="mb-3 text-[10px] font-semibold uppercase tracking-[0.12em] text-[--text-dim]">Pipeline</p>
          <div className="relative">
            {PIPELINE.map((node, idx) => {
              const health = node.serviceKey ? healthMap[node.serviceKey] : null;
              const isUp = health?.status === 'up';
              const isLogical = node.serviceKey === null;
              const latency = health?.latency_ms;
              const isLast = idx === PIPELINE.length - 1;

              return (
                <div key={node.id} className="relative flex gap-3">
                  {/* Connector line */}
                  <div className="flex flex-col items-center">
                    <div
                      className="relative mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded"
                      style={{
                        backgroundColor: isLogical ? '#21262D' : `${node.color}18`,
                        border: `1px solid ${isLogical ? '#30363D' : `${node.color}40`}`,
                      }}
                    >
                      {!isLogical && (
                        <span
                          className="h-1.5 w-1.5 rounded-full"
                          style={{
                            backgroundColor: isUp ? node.color : '#F85149',
                            boxShadow: isUp ? `0 0 4px ${node.color}` : 'none',
                          }}
                        />
                      )}
                      {isLogical && (
                        <span className="h-1.5 w-1.5 rounded-full bg-[--text-dim]" />
                      )}
                    </div>
                    {!isLast && (
                      <div className="w-px flex-1 bg-[--border]" style={{ minHeight: 8 }} />
                    )}
                  </div>

                  {/* Node info */}
                  <div className="pb-2 pt-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span
                        className={cn('text-[11px] font-medium leading-none', isLogical && 'text-[--text-dim]')}
                        style={!isLogical ? { color: isUp ? node.color : '#F85149' } : undefined}
                      >
                        {node.label}
                      </span>
                      {latency !== null && latency !== undefined && (
                        <span className={cn(
                          'font-mono text-[9px]',
                          latency < 100 ? 'text-[--accent-green]' :
                          latency < 300 ? 'text-[--accent-yellow]' : 'text-[--accent-red]'
                        )}>
                          {latency}ms
                        </span>
                      )}
                    </div>
                    <p className="mt-0.5 font-mono text-[9px] text-[--text-dim]">{node.sublabel}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Nav */}
        <div className="border-t border-[--border] px-3 pt-4 pb-2">
          <p className="mb-2 px-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-[--text-dim]">Views</p>
          <nav className="space-y-0.5">
            {NAV.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) => cn(
                  'group flex items-center gap-2.5 rounded-md px-2 py-2 text-[13px] font-medium transition-colors',
                  isActive
                    ? 'bg-[--bg-elevated] text-[--text-primary]'
                    : 'text-[--text-muted] hover:bg-[--bg-elevated] hover:text-[--text-primary]',
                )}
              >
                {({ isActive }: { isActive: boolean }) => (
                  <>
                    <Icon
                      className={cn('h-4 w-4 shrink-0', isActive ? 'text-[--accent-cyan]' : 'text-[--text-dim] group-hover:text-[--text-muted]')}
                      strokeWidth={1.75}
                    />
                    <span>{label}</span>
                    {isActive && (
                      <span className="ml-auto h-1.5 w-1.5 rounded-full bg-[--accent-cyan]" />
                    )}
                  </>
                )}
              </NavLink>
            ))}
          </nav>
        </div>

      </div>{/* end scrollable */}

      {/* Footer: uptime + user */}
      <div className="shrink-0 border-t border-[--border] px-4 py-3">
        <div className="mb-2 flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-[--accent-green]" style={{ boxShadow: '0 0 4px #3FB950' }} />
          <span className="font-mono text-[10px] text-[--text-dim]">UP {uptimeDisplay}</span>
        </div>
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[--bg-elevated] border border-[--border] text-[9px] font-bold uppercase text-[--accent-cyan]">
              {username?.[0] ?? '?'}
            </div>
            <span className="truncate text-[11px] font-medium text-[--text-secondary]">{username}</span>
          </div>
          <button
            onClick={logout}
            title="Sign out"
            className="rounded p-1 text-[--text-dim] transition-colors hover:bg-[--bg-elevated] hover:text-[--accent-red]"
          >
            <LogOut className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </aside>
  );
}
