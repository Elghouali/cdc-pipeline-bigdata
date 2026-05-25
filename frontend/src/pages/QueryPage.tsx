import { useState, useRef } from 'react';
import { Play, RotateCcw, AlertCircle, ChevronRight, ChevronDown, Download } from 'lucide-react';
import { runQuery } from '@/lib/api';
import { cn } from '@/lib/utils';
import type { QueryRow } from '@/types/api';

type ColType = 'number' | 'boolean' | 'date' | 'string';

function inferType(val: unknown): ColType {
  if (typeof val === 'number') return 'number';
  if (typeof val === 'string' && !isNaN(Number(val)) && val.trim() !== '') return 'number';
  if (typeof val === 'boolean' || val === 'true' || val === 'false') return 'boolean';
  if (typeof val === 'string' && /^\d{4}-\d{2}-\d{2}/.test(val)) return 'date';
  return 'string';
}

const TYPE_BADGE: Record<ColType, { label: string; color: string; bg: string }> = {
  number:  { label: 'INT',       color: '#FFA657', bg: '#FFA65720' },
  boolean: { label: 'BOOL',      color: '#3FB950', bg: '#3FB95020' },
  date:    { label: 'TIMESTAMP', color: '#BC8CFF', bg: '#BC8CFF20' },
  string:  { label: 'STRING',    color: '#58A6FF', bg: '#58A6FF20' },
};

const EXAMPLE_QUERIES = [
  {
    label: 'Gold — Top Customers',
    sql: `SELECT customer_name, COUNT(*) AS order_count,
  SUM(gross_revenue) AS total_revenue
FROM iceberg.analytics.gold_sales_facts
GROUP BY customer_name
ORDER BY total_revenue DESC
LIMIT 10`,
  },
  {
    label: 'Silver — Recent Orders',
    sql: `SELECT order_id, customer_id, order_date, status, amount
FROM iceberg.silver.silver_orders
ORDER BY order_date DESC
LIMIT 20`,
  },
  {
    label: 'Bronze — CDC Events',
    sql: `SELECT op, table_name, changed_at, payload
FROM iceberg.bronze.bronze_cdc_events
ORDER BY changed_at DESC
LIMIT 15`,
  },
  {
    label: 'Table Sizes',
    sql: `SELECT table_catalog, table_schema, table_name
FROM system.metadata.table_statistics
WHERE table_catalog = 'iceberg'
ORDER BY row_count DESC`,
  },
];

const TABLE_TREE = [
  {
    layer: 'Bronze', color: '#B08050',
    tables: [
      { name: 'bronze_cdc_events', cols: ['op', 'table_name', 'changed_at', 'payload'] },
      { name: 'bronze_orders',     cols: ['order_id', 'customer_id', 'amount', 'created_at'] },
    ],
  },
  {
    layer: 'Silver', color: '#8B949E',
    tables: [
      { name: 'silver_orders',    cols: ['order_id', 'customer_id', 'status', 'amount', 'order_date'] },
      { name: 'silver_customers', cols: ['customer_id', 'name', 'email', 'created_at'] },
    ],
  },
  {
    layer: 'Gold', color: '#D29922',
    tables: [
      { name: 'gold_sales_facts',    cols: ['customer_name', 'order_count', 'gross_revenue', 'date'] },
      { name: 'gold_daily_summary',  cols: ['date', 'total_orders', 'total_revenue', 'returns'] },
    ],
  },
];

function formatCellValue(val: unknown): string {
  if (val === null || val === undefined) return 'NULL';
  if (typeof val === 'object') return JSON.stringify(val);
  return String(val);
}

function exportCsv(cols: string[], rows: QueryRow[]) {
  const lines = [cols.join(','), ...rows.map(r => cols.map(c => JSON.stringify(formatCellValue(r[c]))).join(','))];
  const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href = url; a.download = 'query_result.csv'; a.click();
  URL.revokeObjectURL(url);
}

export function QueryPage() {
  const [sql, setSql] = useState(EXAMPLE_QUERIES[0].sql);
  const [rows, setRows] = useState<QueryRow[] | null>(null);
  const [cols, setCols] = useState<string[]>([]);
  const [colTypes, setColTypes] = useState<Record<string, ColType>>({});
  const [running, setRunning] = useState(false);
  const [error, setError] = useState('');
  const [elapsed, setElapsed] = useState<number | null>(null);
  const [expandedLayers, setExpandedLayers] = useState<Set<string>>(new Set(['Gold']));
  const ctrlRef = useRef<AbortController | null>(null);

  async function runIt() {
    if (!sql.trim() || running) return;
    ctrlRef.current?.abort();
    ctrlRef.current = new AbortController();
    setRunning(true); setError(''); setRows(null);
    const t0 = performance.now();
    try {
      const data = await runQuery(sql.trim(), ctrlRef.current.signal);
      setElapsed(performance.now() - t0);
      if (data.length > 0) {
        const columns = Object.keys(data[0]);
        setCols(columns);
        const types: Record<string, ColType> = {};
        columns.forEach(col => { types[col] = inferType(data[0][col]); });
        setColTypes(types);
      } else {
        setCols([]); setColTypes({});
      }
      setRows(data);
    } catch (e: unknown) {
      if ((e as Error)?.name === 'AbortError') return;
      setError(e instanceof Error ? e.message : 'Query failed');
    } finally {
      setRunning(false);
    }
  }

  function toggleLayer(name: string) {
    setExpandedLayers(prev => {
      const next = new Set(prev);
      next.has(name) ? next.delete(name) : next.add(name);
      return next;
    });
  }

  return (
    <div className="page-enter flex h-[calc(100vh-56px)] flex-col p-6">
      <div className="mb-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[--text-dim]">Trino · Iceberg · Distributed SQL</p>
        <h1 className="mt-0.5 text-xl font-bold text-[--text-primary]">Query Console</h1>
      </div>

      <div className="flex flex-1 gap-4 overflow-hidden">

        {/* Left: table browser */}
        <div className="w-52 shrink-0 overflow-y-auto rounded-lg border border-[--border] bg-[--bg-surface]">
          <div className="border-b border-[--border] bg-[--bg-elevated] px-3 py-2">
            <p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[--text-dim]">Tables</p>
          </div>
          <div className="p-2">
            {TABLE_TREE.map(({ layer, color, tables }) => {
              const expanded = expandedLayers.has(layer);
              return (
                <div key={layer} className="mb-1">
                  <button
                    onClick={() => toggleLayer(layer)}
                    className="flex w-full items-center gap-1.5 rounded px-2 py-1.5 text-left transition-colors hover:bg-[--bg-elevated]"
                  >
                    {expanded
                      ? <ChevronDown className="h-3 w-3 shrink-0 text-[--text-dim]" />
                      : <ChevronRight className="h-3 w-3 shrink-0 text-[--text-dim]" />
                    }
                    <span className="h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
                    <span className="text-[11px] font-medium text-[--text-primary]">{layer}</span>
                  </button>
                  {expanded && tables.map(t => (
                    <div key={t.name} className="ml-4 mt-0.5">
                      <button
                        onClick={() => setSql(`SELECT *\nFROM iceberg.${layer.toLowerCase()}.${t.name}\nLIMIT 20`)}
                        className="w-full rounded px-2 py-1 text-left transition-colors hover:bg-[--bg-elevated]"
                      >
                        <p className="truncate font-mono text-[10px] text-[--text-muted]">{t.name}</p>
                      </button>
                      {t.cols.map(col => (
                        <p key={col} className="ml-2 truncate px-2 py-0.5 font-mono text-[9px] text-[--text-dim]">
                          · {col}
                        </p>
                      ))}
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: editor + results */}
        <div className="flex flex-1 flex-col gap-4 overflow-hidden">
          {/* Example queries */}
          <div className="flex flex-wrap gap-1.5">
            {EXAMPLE_QUERIES.map(q => (
              <button
                key={q.label}
                onClick={() => setSql(q.sql)}
                className="rounded-md border border-[--border] bg-[--bg-surface] px-2.5 py-1 text-[11px] text-[--text-muted] transition-colors hover:bg-[--bg-elevated] hover:text-[--text-primary]"
              >
                {q.label}
              </button>
            ))}
          </div>

          {/* SQL editor */}
          <div className="rounded-lg border border-[--border] bg-[--bg-surface] overflow-hidden">
            <div className="flex items-center justify-between border-b border-[--border] bg-[--bg-elevated] px-4 py-2">
              <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-[--text-dim]">SQL · Trino dialect</span>
              <div className="flex items-center gap-2">
                {rows !== null && (
                  <button
                    onClick={() => { setRows(null); setError(''); setElapsed(null); }}
                    className="flex items-center gap-1 rounded px-2 py-1 text-[11px] text-[--text-dim] transition-colors hover:bg-[--bg-surface] hover:text-[--text-muted]"
                  >
                    <RotateCcw className="h-3 w-3" /> Clear
                  </button>
                )}
                <button
                  onClick={runIt}
                  disabled={running || !sql.trim()}
                  className={cn(
                    'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-[11px] font-semibold transition-all active:scale-[0.97]',
                    running || !sql.trim()
                      ? 'cursor-not-allowed bg-[--bg-surface] text-[--text-dim] opacity-50'
                      : 'bg-[#00D4FF20] text-[--accent-cyan] hover:bg-[#00D4FF30]'
                  )}
                >
                  <Play className="h-3 w-3" />
                  {running ? 'Running…' : 'Run Query'}
                </button>
              </div>
            </div>
            <textarea
              value={sql}
              onChange={e => setSql(e.target.value)}
              onKeyDown={e => { if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); void runIt(); } }}
              spellCheck={false}
              rows={7}
              className="w-full resize-none bg-transparent p-4 font-mono text-sm text-[--text-primary] outline-none placeholder-[--text-dim]"
              style={{ caretColor: '#00D4FF', lineHeight: 1.65 }}
              placeholder="SELECT * FROM iceberg.analytics.gold_sales_facts LIMIT 10"
            />
            <div className="flex items-center justify-between border-t border-[--border] bg-[--bg-elevated] px-4 py-1.5">
              <span className="font-mono text-[10px] text-[--text-dim]">
                {sql.trim().split('\n').length} lines · Ctrl+Enter to run
              </span>
              {elapsed !== null && (
                <span className="font-mono text-[10px] text-[--accent-green]">{elapsed.toFixed(0)}ms</span>
              )}
            </div>
          </div>

          {error && (
            <div className="flex items-start gap-2.5 rounded-lg border border-[#F85149]/20 bg-[#F85149]/8 px-4 py-3">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-[#F85149]" />
              <p className="font-mono text-xs text-[#F85149]">{error}</p>
            </div>
          )}

          {rows !== null && (
            <div className="flex flex-1 flex-col overflow-hidden rounded-lg border border-[--border] bg-[--bg-surface]">
              <div className="flex items-center justify-between border-b border-[--border] bg-[--bg-elevated] px-4 py-2">
                <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[--text-dim]">
                  Results · {rows.length} row{rows.length !== 1 ? 's' : ''} · {cols.length} col{cols.length !== 1 ? 's' : ''}
                </span>
                {rows.length > 0 && (
                  <button
                    onClick={() => exportCsv(cols, rows)}
                    className="flex items-center gap-1 text-[10px] text-[--text-dim] transition-colors hover:text-[--text-muted]"
                  >
                    <Download className="h-3 w-3" /> Export CSV
                  </button>
                )}
              </div>

              {rows.length === 0 ? (
                <div className="flex items-center justify-center py-12 text-sm text-[--text-muted]">
                  No rows returned.
                </div>
              ) : (
                <div className="flex-1 overflow-auto">
                  <table className="w-full text-[12px]">
                    <thead className="sticky top-0 bg-[--bg-surface]">
                      <tr className="border-b border-[--border]">
                        {cols.map(col => {
                          const tb = TYPE_BADGE[colTypes[col] ?? 'string'];
                          return (
                            <th key={col} className="px-4 py-2.5 text-left">
                              <div className="flex items-center gap-1.5">
                                <span
                                  className="rounded px-1.5 py-0.5 font-mono text-[8px] font-bold uppercase tracking-wider"
                                  style={{ color: tb.color, backgroundColor: tb.bg }}
                                >
                                  {tb.label}
                                </span>
                                <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.05em] text-[--text-muted]">
                                  {col}
                                </span>
                              </div>
                            </th>
                          );
                        })}
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((row, ri) => (
                        <tr key={ri} className="border-b border-[--border-subtle] transition-colors last:border-0 hover:bg-[--bg-elevated]">
                          {cols.map(col => {
                            const t = colTypes[col] ?? 'string';
                            const raw = row[col];
                            const isNull = raw === null || raw === undefined;
                            return (
                              <td
                                key={col}
                                className={cn(
                                  'max-w-[240px] truncate px-4 py-2.5 font-mono',
                                  isNull          ? 'italic text-[--text-dim]' :
                                  t === 'number'  ? 'tabular-nums text-[#FFA657]' :
                                  t === 'boolean' ? (raw ? 'text-[--accent-green]' : 'text-[--accent-red]') :
                                  t === 'date'    ? 'text-[#BC8CFF]' :
                                                   'text-[--text-primary]'
                                )}
                              >
                                {formatCellValue(raw)}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
