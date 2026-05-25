import { useEffect, useRef, useState } from 'react';
import { Filter, Pause, Play } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { cn } from '@/lib/utils';

type OpType = 'INSERT' | 'UPDATE' | 'DELETE';
interface StreamEvent {
  id: number; ts: string; ms: number; op: OpType;
  topic: string; key: string; payload: string;
}

const TOPICS = ['orders', 'customers', 'payments', 'returns', 'products'];
const NAMES  = ['Karim B.', 'Fatima Z.', 'Youssef E.', 'Amina L.', 'Hassan M.', 'Sara A.', 'Omar R.'];
const OPS: OpType[] = ['INSERT', 'INSERT', 'INSERT', 'UPDATE', 'UPDATE', 'DELETE'];

const OP_BADGE: Record<OpType, 'success' | 'warning' | 'error'> = {
  INSERT: 'success', UPDATE: 'warning', DELETE: 'error',
};
const OP_COLOR: Record<OpType, string> = {
  INSERT: '#3FB950', UPDATE: '#D29922', DELETE: '#F85149',
};

function makeEvent(id: number): StreamEvent {
  const op = OPS[Math.floor(Math.random() * OPS.length)];
  const topic = TOPICS[Math.floor(Math.random() * TOPICS.length)];
  const name = NAMES[Math.floor(Math.random() * NAMES.length)];
  const amount = (Math.random() * 1200 + 50).toFixed(2);
  const now = new Date();
  const ms = now.getMilliseconds();
  const ts = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}:${String(now.getSeconds()).padStart(2,'0')}.${String(ms).padStart(3,'0')}`;
  const payload =
    op === 'DELETE' ? `id:${1000 + id} removed` :
    topic === 'orders' ? `${name} · ${amount} MAD` :
    topic === 'customers' ? `${name} · email updated` :
    `id:${1000 + id} · ${amount} MAD`;
  return { id, ts, ms, op, topic, key: `${topic}:${1000 + id}`, payload };
}

export function StatsPage() {
  const [events, setEvents] = useState<StreamEvent[]>(() =>
    Array.from({ length: 20 }, (_, i) => makeEvent(i))
  );
  const [paused, setPaused] = useState(false);
  const [filterOp, setFilterOp] = useState<Set<OpType>>(new Set(['INSERT', 'UPDATE', 'DELETE']));
  const [filterTopic, setFilterTopic] = useState('');
  const [view, setView] = useState<'table' | 'timeline'>('table');
  const eventIdRef = useRef(200);

  useEffect(() => {
    if (paused) return;
    const id = setInterval(() => {
      const newEv = makeEvent(eventIdRef.current++);
      setEvents(prev => [newEv, ...prev.slice(0, 199)]);
    }, 800 + Math.random() * 1200);
    return () => clearInterval(id);
  }, [paused]);

  const filtered = events.filter(e =>
    filterOp.has(e.op) &&
    (filterTopic === '' || e.topic.includes(filterTopic.toLowerCase()))
  );

  const total = events.length || 1;
  const insertCount = events.filter(e => e.op === 'INSERT').length;
  const updateCount = events.filter(e => e.op === 'UPDATE').length;
  const deleteCount = events.filter(e => e.op === 'DELETE').length;

  return (
    <div className="page-enter flex h-[calc(100vh-56px)] flex-col p-6">
      <div className="mb-4 flex items-start justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[--text-dim]">Kafka Topics</p>
          <h1 className="mt-0.5 text-xl font-bold text-[--text-primary]">Event Stream</h1>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex overflow-hidden rounded-md border border-[--border] bg-[--bg-elevated]">
            {(['table', 'timeline'] as const).map(v => (
              <button
                key={v}
                onClick={() => setView(v)}
                className={cn(
                  'px-3 py-1.5 text-[11px] font-medium capitalize transition-colors',
                  view === v ? 'bg-[--bg-surface] text-[--text-primary]' : 'text-[--text-dim] hover:text-[--text-muted]'
                )}
              >
                {v}
              </button>
            ))}
          </div>
          <button
            onClick={() => setPaused(p => !p)}
            className={cn(
              'flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-[11px] font-medium transition-colors',
              paused
                ? 'border-[--accent-green]/30 bg-[#3FB950]/10 text-[--accent-green]'
                : 'border-[--border] bg-[--bg-surface] text-[--text-muted] hover:bg-[--bg-elevated]'
            )}
          >
            {paused ? <Play className="h-3 w-3" /> : <Pause className="h-3 w-3" />}
            {paused ? 'Resume' : 'Pause'}
          </button>
        </div>
      </div>

      {/* Stats bar */}
      <div className="mb-4 grid grid-cols-4 gap-3">
        {[
          { label: 'Total Events', value: events.length, pct: null, color: '#E6EDF3' },
          { label: 'INSERT', value: insertCount, pct: Math.round(insertCount / total * 100), color: '#3FB950' },
          { label: 'UPDATE', value: updateCount, pct: Math.round(updateCount / total * 100), color: '#D29922' },
          { label: 'DELETE', value: deleteCount, pct: Math.round(deleteCount / total * 100), color: '#F85149' },
        ].map(s => (
          <div key={s.label} className="rounded-lg border border-[--border] bg-[--bg-surface] p-4">
            <p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[--text-dim]">{s.label}</p>
            <div className="mt-1 flex items-baseline gap-1.5">
              <span className="font-mono text-xl font-light" style={{ color: s.color }}>{s.value}</span>
              {s.pct !== null && (
                <span className="font-mono text-[10px]" style={{ color: `${s.color}80` }}>{s.pct}%</span>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <Filter className="h-3.5 w-3.5 shrink-0 text-[--text-dim]" />
        <div className="flex gap-1.5">
          {(['INSERT', 'UPDATE', 'DELETE'] as OpType[]).map(op => (
            <button
              key={op}
              onClick={() => {
                setFilterOp(prev => {
                  const next = new Set(prev);
                  next.has(op) ? next.delete(op) : next.add(op);
                  return next;
                });
              }}
              className={cn('rounded border px-2.5 py-1 font-mono text-[10px] font-semibold uppercase tracking-[0.08em] transition-all', !filterOp.has(op) && 'opacity-30')}
              style={filterOp.has(op)
                ? { borderColor: `${OP_COLOR[op]}50`, backgroundColor: `${OP_COLOR[op]}15`, color: OP_COLOR[op] }
                : { borderColor: '#30363D', color: '#484F58' }}
            >
              {op}
            </button>
          ))}
        </div>
        <input
          value={filterTopic}
          onChange={e => setFilterTopic(e.target.value)}
          placeholder="Filter by table…"
          className="h-7 w-44 rounded-md border border-[--border] bg-[--bg-elevated] px-2.5 font-mono text-[11px] text-[--text-primary] placeholder-[--text-dim] outline-none focus:border-[--accent-cyan]"
        />
        <span className="ml-auto font-mono text-[10px] text-[--text-dim]">{filtered.length} events</span>
        {!paused && (
          <div className="flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-[--accent-green] node-glow" />
            <span className="font-mono text-[10px] text-[--accent-green]">LIVE</span>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden rounded-lg border border-[--border] bg-[--bg-surface]">
        {view === 'table' ? (
          <>
            <div className="grid grid-cols-[140px_72px_100px_180px_1fr] border-b border-[--border] bg-[--bg-elevated] px-4 py-2.5">
              {['Timestamp', 'Op', 'Topic', 'Key', 'Payload'].map(h => (
                <span key={h} className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[--text-dim]">{h}</span>
              ))}
            </div>
            <div className="h-[calc(100%-40px)] overflow-y-auto">
              {filtered.map((ev, idx) => (
                <div
                  key={ev.id}
                  className={cn(
                    'grid grid-cols-[140px_72px_100px_180px_1fr] items-center border-b border-[--border-subtle] px-4 py-2 transition-colors last:border-0 hover:bg-[--bg-elevated]',
                    idx === 0 && !paused && 'event-enter'
                  )}
                >
                  <span className="font-mono text-[10px] text-[--text-dim]">{ev.ts}</span>
                  <Badge variant={OP_BADGE[ev.op]}>{ev.op}</Badge>
                  <span className="font-mono text-[10px] text-[--text-muted]">{ev.topic}</span>
                  <span className="truncate font-mono text-[10px] text-[--text-dim]">{ev.key}</span>
                  <span className="truncate font-mono text-[10px] text-[--text-muted]">{ev.payload}</span>
                </div>
              ))}
            </div>
          </>
        ) : (
          <TimelineView events={filtered} />
        )}
      </div>
    </div>
  );
}

function TimelineView({ events }: { events: StreamEvent[] }) {
  const topicGroups: Record<string, StreamEvent[]> = {};
  for (const e of events.slice(0, 80)) {
    if (!topicGroups[e.topic]) topicGroups[e.topic] = [];
    topicGroups[e.topic].push(e);
  }
  return (
    <div className="h-full overflow-y-auto p-6 space-y-4">
      {Object.entries(topicGroups).map(([topic, evs]) => (
        <div key={topic} className="flex items-center gap-4">
          <span className="w-20 shrink-0 text-right font-mono text-[11px] text-[--text-muted]">{topic}</span>
          <div className="flex flex-1 items-center gap-1 overflow-hidden">
            {evs.map(ev => (
              <div
                key={ev.id}
                title={`${ev.op} · ${ev.payload}`}
                className="h-6 w-6 shrink-0 cursor-default rounded transition-transform hover:scale-125"
                style={{ backgroundColor: `${OP_COLOR[ev.op]}50`, border: `1px solid ${OP_COLOR[ev.op]}80` }}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
