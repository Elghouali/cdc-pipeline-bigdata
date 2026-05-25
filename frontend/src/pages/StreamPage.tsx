import { useState, useEffect } from 'react';
import { Filter, Search, Activity, List } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { cn } from '@/lib/utils';

export function StreamPage() {
  const [view, setView] = useState<'table' | 'timeline'>('table');
  
  // Mock data setup
  const [events, setEvents] = useState<any[]>([]);
  
  useEffect(() => {
    // initial mock events
    const initial = Array.from({ length: 50 }).map((_, i) => ({
      id: 1000 + i,
      ts: new Date(Date.now() - i * 1000).toISOString().split('T')[1].slice(0, -1),
      op: ['INSERT', 'UPDATE', 'DELETE'][Math.floor(Math.random() * 3)],
      table: ['orders', 'customers', 'payments'][Math.floor(Math.random() * 3)],
      payload: `test payload ${i}`
    }));
    setEvents(initial);
  }, []);

  return (
    <div className="flex h-full flex-col page-enter">
      {/* Filters Bar */}
      <div className="flex shrink-0 items-center justify-between border-b border-[--border] bg-[--bg-surface] p-4">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 rounded-md border border-[--border] bg-[--bg-elevated] px-3 py-1.5 text-sm">
            <Search className="h-4 w-4 text-[--text-muted]" />
            <input 
              type="text" 
              placeholder="Search table name..." 
              className="bg-transparent text-[--text-primary] placeholder-[--text-dim] outline-none"
            />
          </div>
          
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-[--text-muted]" />
            <select className="rounded-md border border-[--border] bg-[--bg-elevated] px-3 py-1.5 text-sm text-[--text-primary] outline-none">
              <option>All Topics</option>
              <option>cdc.public.orders</option>
              <option>cdc.public.customers</option>
            </select>
          </div>
        </div>

        <div className="flex items-center gap-6">
          <div className="flex items-center gap-4 text-xs font-mono text-[--text-dim]">
            <span>142 ev/s</span>
            <span className="text-[--accent-green]">IN: 60%</span>
            <span className="text-[--accent-yellow]">UP: 30%</span>
            <span className="text-[--accent-red]">DE: 10%</span>
          </div>

          <div className="flex items-center rounded-md border border-[--border] bg-[--bg-elevated] p-0.5">
            <button
              onClick={() => setView('table')}
              className={cn(
                'rounded px-2 py-1 flex items-center gap-1.5 text-xs font-medium transition-colors',
                view === 'table' ? 'bg-[--bg-surface] text-[--text-primary] shadow-sm' : 'text-[--text-muted] hover:text-[--text-primary]'
              )}
            >
              <List className="h-3.5 w-3.5" /> Table
            </button>
            <button
              onClick={() => setView('timeline')}
              className={cn(
                'rounded px-2 py-1 flex items-center gap-1.5 text-xs font-medium transition-colors',
                view === 'timeline' ? 'bg-[--bg-surface] text-[--text-primary] shadow-sm' : 'text-[--text-muted] hover:text-[--text-primary]'
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
          <div className="rounded-lg border border-[--border] bg-[--bg-surface] overflow-hidden">
            <div className="grid grid-cols-[150px_100px_200px_1fr] border-b border-[--border] bg-[--bg-elevated] px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.08em] text-[--text-dim]">
              <span>Timestamp</span>
              <span>Operation</span>
              <span>Table</span>
              <span>Payload</span>
            </div>
            <div className="divide-y divide-[--border-subtle]">
              {events.map((ev, i) => (
                <div key={i} className="grid grid-cols-[150px_100px_200px_1fr] items-center px-4 py-2 hover:bg-[--bg-elevated] transition-colors">
                  <span className="font-mono text-[11px] text-[--text-dim]">{ev.ts}</span>
                  <div>
                    <Badge variant={ev.op === 'INSERT' ? 'success' : ev.op === 'UPDATE' ? 'warning' : 'error'}>{ev.op}</Badge>
                  </div>
                  <span className="font-mono text-[11px] text-[--text-muted]">{ev.table}</span>
                  <span className="truncate font-mono text-[11px] text-[--text-dim]">{ev.payload}</span>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex h-full items-center justify-center text-[--text-muted]">
            Timeline view visualization would be rendered here using recharts or d3.
          </div>
        )}
      </div>
    </div>
  );
}
