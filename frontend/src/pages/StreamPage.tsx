import { useState, useEffect, useRef } from 'react';
import { Filter, Search, Activity, List } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { cn } from '@/lib/utils';
import { useAuth } from '@/context/AuthContext';
import type { SseEvent, SseOp } from '@/types/api';

const CDC_TOPICS = [
  'cdc.public.orders',
  'cdc.public.customers',
  'cdc.public.payments',
  'cdc.public.returns',
  'cdc.public.products',
  'cdc.public.order_items',
];

const OP_LABEL: Record<SseOp, string> = {
  c: 'INSERT',
  u: 'UPDATE',
  d: 'DELETE',
  r: 'READ',
};

const OP_VARIANT: Record<SseOp, 'success' | 'warning' | 'error' | 'muted'> = {
  c: 'success',
  u: 'warning',
  d: 'error',
  r: 'muted',
};

const MAX_EVENTS = 200;

function formatTs(ts: number | null): string {
  if (ts == null) return '—';
  const d = new Date(ts);
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}.${String(d.getMilliseconds()).padStart(3, '0')}`;
}

export function StreamPage() {
  const [view, setView] = useState<'table' | 'timeline'>('table');
  const [events, setEvents] = useState<SseEvent[]>([]);
  const [search, setSearch] = useState('');
  const [topicFilter, setTopicFilter] = useState('');
  const [connected, setConnected] = useState(false);
  const eventIdRef = useRef(0);
  const { token, logout } = useAuth();

  useEffect(() => {
    if (!token) return;
    const accessToken = token;
    const controller = new AbortController();
    const signal = controller.signal;
    let retry: ReturnType<typeof setTimeout> | undefined;

    async function connect() {
      try {
        const res = await fetch('/api/events/stream', {
          headers: { Authorization: `Bearer ${accessToken}` },
          signal,
          cache: 'no-store',
        });
        if (res.status === 401) {
          logout();
          return;
        }
        if (!res.ok || !res.body) throw new Error('Event stream unavailable');
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        try {
          while (!signal.aborted) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            // The server emits LF-delimited SSE frames. Bound partial input.
            if (buffer.length > 65536) throw new Error('Invalid event frame');
            let end: number;
            while ((end = buffer.indexOf('\n\n')) !== -1) {
              const frame = buffer.slice(0, end);
              buffer = buffer.slice(end + 2);
              if (signal.aborted) return;
              const lines = frame.split('\n');
              const event = lines.find(line => line.startsWith('event: '))?.slice(7);
              const data = lines.find(line => line.startsWith('data: '))?.slice(6);
              if (event === 'ready') setConnected(true);
              if (event === 'error') setConnected(false);
              if (event === 'change' && data) {
                try {
                  const parsed = JSON.parse(data) as Omit<SseEvent, 'id'>;
                  const id = eventIdRef.current++;
                  setEvents(prev => [{ ...parsed, id }, ...prev.slice(0, MAX_EVENTS - 1)]);
                } catch { /* malformed SSE frame */ }
              }
            }
          }
        } finally {
          await reader.cancel().catch(() => undefined);
          reader.releaseLock();
        }
      } catch {
        // A bounded retry handles temporary service failures.
      } finally {
        if (!signal.aborted) {
          setConnected(false);
          retry = setTimeout(() => { void connect(); }, 3000);
        }
      }
    }

    void connect();
    return () => {
      controller.abort();
      if (retry !== undefined) clearTimeout(retry);
      setConnected(false);
    };
  }, [token, logout]);

  const filtered = events.filter(ev => {
    if (search && !ev.table.toLowerCase().includes(search.toLowerCase())) return false;
    if (topicFilter && ev.topic !== topicFilter) return false;
    return true;
  });

  // Live op-ratio stats
  const total = events.length;
  const inserts = events.filter(e => e.op === 'c').length;
  const updates = events.filter(e => e.op === 'u').length;
  const deletes = events.filter(e => e.op === 'd').length;

  return (
    <div className="flex h-full flex-col page-enter">

      {/* Filters Bar */}
      <div className="flex shrink-0 items-center justify-between border-b border-[--border] bg-[--bg-surface] p-4">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 rounded-md border border-[--border] bg-[--bg-elevated] px-3 py-1.5 text-sm">
            <Search className="h-4 w-4 text-[--text-muted]" />
            <input
              type="text"
              placeholder="Search table name…"
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="bg-transparent text-[--text-primary] placeholder:text-[--text-dim] outline-none"
            />
          </div>

          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-[--text-muted]" />
            <select
              value={topicFilter}
              onChange={e => setTopicFilter(e.target.value)}
              className="rounded-md border border-[--border] bg-[--bg-elevated] px-3 py-1.5 text-sm text-[--text-primary] outline-none"
            >
              <option value="">All Topics</option>
              {CDC_TOPICS.map(t => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex items-center gap-6">
          {/* Live stats */}
          <div className="flex items-center gap-4 font-mono text-xs text-[--text-dim]">
            <span className="flex items-center gap-1.5">
              <span
                className={cn('h-1.5 w-1.5 rounded-full', connected ? 'bg-[--accent-green]' : 'bg-[--accent-red]')}
              />
              {connected ? 'Connected' : 'Disconnected'}
            </span>
            {total > 0 && (
              <>
                <span className="text-[--accent-green]">
                  IN: {Math.round((inserts / total) * 100)}%
                </span>
                <span className="text-[--accent-yellow]">
                  UP: {Math.round((updates / total) * 100)}%
                </span>
                <span className="text-[--accent-red]">
                  DE: {Math.round((deletes / total) * 100)}%
                </span>
              </>
            )}
          </div>

          {/* View toggle */}
          <div className="flex items-center rounded-md border border-[--border] bg-[--bg-elevated] p-0.5">
            <button
              onClick={() => setView('table')}
              className={cn(
                'flex items-center gap-1.5 rounded px-2 py-1 text-xs font-medium transition-colors',
                view === 'table'
                  ? 'bg-[--bg-surface] text-[--text-primary] shadow-sm'
                  : 'text-[--text-muted] hover:text-[--text-primary]'
              )}
            >
              <List className="h-3.5 w-3.5" /> Table
            </button>
            <button
              onClick={() => setView('timeline')}
              className={cn(
                'flex items-center gap-1.5 rounded px-2 py-1 text-xs font-medium transition-colors',
                view === 'timeline'
                  ? 'bg-[--bg-surface] text-[--text-primary] shadow-sm'
                  : 'text-[--text-muted] hover:text-[--text-primary]'
              )}
            >
              <Activity className="h-3.5 w-3.5" /> Timeline
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto bg-[--bg-base] p-6">
        {view === 'table' ? (
          <div className="rounded-xl border border-[--border] bg-[--bg-surface] overflow-hidden shadow-[var(--shadow-sm)]">
            <div className="grid grid-cols-[150px_100px_200px_1fr] border-b border-[--border] bg-[--bg-elevated] px-4 py-3 text-[11px] font-semibold uppercase tracking-widest text-[--text-dim]">
              <span>Timestamp</span>
              <span>Operation</span>
              <span>Table</span>
              <span>Payload</span>
            </div>
            <div className="divide-y divide-[--border-subtle]">
              {filtered.length === 0 ? (
                <div className="p-8 text-center text-sm text-[--text-muted]">
                  {connected
                    ? events.length === 0
                      ? 'Waiting for CDC events…'
                      : 'No events match the current filter.'
                    : 'Connecting to Kafka stream…'}
                </div>
              ) : (
                filtered.map((ev, i) => (
                  <div
                    key={ev.id}
                    className={cn(
                      'grid grid-cols-[150px_100px_200px_1fr] items-center px-4 py-2 transition-colors hover:bg-[--bg-elevated]',
                      i === 0 && 'event-enter'
                    )}
                  >
                    <span className="font-mono text-[11px] text-[--text-dim]">{formatTs(ev.ts)}</span>
                    <div>
                      <Badge variant={OP_VARIANT[ev.op]}>{OP_LABEL[ev.op]}</Badge>
                    </div>
                    <span className="font-mono text-[11px] text-[--text-muted]">{ev.table}</span>
                    <span className="truncate font-mono text-[11px] text-[--text-dim]">
                      {Object.entries(ev.payload)
                        .slice(0, 3)
                        .map(([k, v]) => `${k}: ${String(v)}`)
                        .join(' · ') || '—'}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        ) : (
          <div className="flex h-full items-center justify-center text-[--text-muted] text-sm">
            Timeline view — {total} events captured.
          </div>
        )}
      </div>
    </div>
  );
}
