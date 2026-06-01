import { useEffect, useRef, useState } from 'react';
import CodeMirror from '@uiw/react-codemirror';
import { sql } from '@codemirror/lang-sql';
import { AlertCircle, Columns, ChevronDown, ChevronRight, Database, Download, History, Play, Table as TableIcon } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { runQuery } from '@/lib/api';
import type { QueryRow } from '@/types/api';

// Mock DB schema for tree
const SCHEMA = [
  {
    layer: 'Bronze',
    tables: [
      { name: 'orders_raw', columns: ['id', 'payload', 'ts'] },
      { name: 'customers_raw', columns: ['id', 'payload', 'ts'] }
    ]
  },
  {
    layer: 'Silver',
    tables: [
      { name: 'orders', columns: ['order_id', 'amount', 'status', 'created_at'] },
      { name: 'customers', columns: ['customer_id', 'email', 'name', 'updated_at'] }
    ]
  }
];

function exportCsv(rows: QueryRow[]): void {
  if (rows.length === 0) return;
  const headers = Object.keys(rows[0]);
  const lines = [
    headers.join(','),
    ...rows.map(r =>
      headers.map(h => {
        const v = String(r[h] ?? '');
        return v.includes(',') || v.includes('"') || v.includes('\n')
          ? `"${v.replace(/"/g, '""')}"`
          : v;
      }).join(',')
    ),
  ];
  const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'query_results.csv';
  a.click();
  URL.revokeObjectURL(url);
}

export function QueryPage() {
  const [query, setQuery] = useState(
    'SELECT\n  order_id,\n  amount,\n  status,\n  created_at\nFROM silver.orders\nWHERE amount > 1000\nORDER BY created_at DESC\nLIMIT 100'
  );
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState<QueryRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [elapsedMs, setElapsedMs] = useState<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Tree state
  const [expandedLayers, setExpandedLayers] = useState<Record<string, boolean>>({ Silver: true });
  const [expandedTables, setExpandedTables] = useState<Record<string, boolean>>({ orders: true });

  // Use a ref so the keydown handler always calls the latest version of handleRun.
  const handleRunRef = useRef<() => void>(() => undefined);

  async function handleRun() {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setRunning(true);
    setError(null);
    setResults(null);
    setElapsedMs(null);
    const t0 = performance.now();
    try {
      const rows = await runQuery(query.trim(), controller.signal);
      setResults(rows);
      setElapsedMs(Math.round(performance.now() - t0));
    } catch (err: unknown) {
      if (err instanceof Error && err.name !== 'AbortError') {
        setError(err.message);
      }
    } finally {
      setRunning(false);
    }
  }

  // Keep ref in sync so Ctrl+Enter never captures a stale closure.
  useEffect(() => { handleRunRef.current = handleRun; });

  // Wire Ctrl+Enter / Cmd+Enter shortcut.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        void handleRunRef.current();
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const toggleLayer = (l: string) => setExpandedLayers(prev => ({ ...prev, [l]: !prev[l] }));
  const toggleTable = (t: string) => setExpandedTables(prev => ({ ...prev, [t]: !prev[t] }));

  const columns = results && results.length > 0 ? Object.keys(results[0]) : [];

  return (
    <div className="flex h-full page-enter">
      {/* Left Sidebar - Table Browser */}
      <div className="w-64 shrink-0 flex flex-col border-r border-[--border] bg-[--bg-surface]">
        <div className="border-b border-[--border] p-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[--text-dim]">Data Explorer</p>
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          {SCHEMA.map(layer => (
            <div key={layer.layer} className="mb-1">
              <button
                onClick={() => toggleLayer(layer.layer)}
                className="flex w-full items-center gap-1.5 rounded p-1.5 text-left transition-colors hover:bg-[--bg-elevated]"
              >
                {expandedLayers[layer.layer]
                  ? <ChevronDown className="h-3.5 w-3.5 text-[--text-dim]" />
                  : <ChevronRight className="h-3.5 w-3.5 text-[--text-dim]" />}
                <Database className="h-3.5 w-3.5 text-[--text-muted]" />
                <span className="text-[13px] font-medium text-[--text-primary]">{layer.layer}</span>
              </button>

              {expandedLayers[layer.layer] && (
                <div className="ml-5 mt-1 space-y-1 border-l border-[--border-subtle] pl-2">
                  {layer.tables.map(table => (
                    <div key={table.name}>
                      <button
                        onClick={() => toggleTable(table.name)}
                        className="flex w-full items-center gap-1.5 rounded p-1.5 text-left transition-colors hover:bg-[--bg-elevated]"
                      >
                        {expandedTables[table.name]
                          ? <ChevronDown className="h-3.5 w-3.5 text-[--text-dim]" />
                          : <ChevronRight className="h-3.5 w-3.5 text-[--text-dim]" />}
                        <TableIcon className="h-3.5 w-3.5 text-[--text-muted]" />
                        <span className="text-[13px] text-[--text-muted] hover:text-[--text-primary]">{table.name}</span>
                      </button>

                      {expandedTables[table.name] && (
                        <div className="ml-5 mt-1 space-y-1">
                          {table.columns.map(col => (
                            <div
                              key={col}
                              className="flex items-center gap-1.5 rounded p-1 px-2 text-[12px] text-[--text-dim] transition-colors hover:bg-[--bg-elevated] hover:text-[--text-muted]"
                            >
                              <Columns className="h-3 w-3" />
                              <span className="font-mono">{col}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Main Content - Editor & Results */}
      <div className="flex flex-1 flex-col overflow-hidden bg-[--bg-base]">

        {/* Editor Actions */}
        <div className="flex shrink-0 items-center justify-between border-b border-[--border] bg-[--bg-surface] p-3">
          <div className="flex items-center gap-2">
            <button
              onClick={() => void handleRun()}
              disabled={running}
              className="flex items-center gap-1.5 rounded-lg bg-[--accent] px-3.5 py-1.5 text-[13px] font-semibold text-white transition-all hover:bg-[--accent-hover] active:scale-95 disabled:opacity-50"
            >
              <Play className="h-4 w-4" fill="currentColor" />
              {running ? 'Running…' : 'Run Query'}
            </button>
            <span className="font-mono text-[10px] text-[--text-dim]">Ctrl + Enter</span>
          </div>

          <button className="flex items-center gap-1.5 rounded border border-[--border] bg-[--bg-elevated] px-3 py-1.5 text-xs text-[--text-muted] hover:text-[--text-primary]">
            <History className="h-3.5 w-3.5" /> History
          </button>
        </div>

        {/* Editor */}
        <div className="shrink-0 border-b border-[--border] bg-[--bg-surface]">
          <CodeMirror
            value={query}
            height="250px"
            theme="dark"
            extensions={[sql()]}
            onChange={(val) => setQuery(val)}
            basicSetup={{ lineNumbers: true, highlightActiveLineGutter: true, foldGutter: true }}
            className="text-[13px] font-mono"
          />
        </div>

        {/* Results */}
        <div className="flex flex-1 flex-col overflow-hidden">
          <div className="flex shrink-0 items-center justify-between border-b border-[--border] bg-[--bg-elevated] px-4 py-2">
            <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[--text-dim]">Results</p>
            {results && results.length > 0 && (
              <button
                onClick={() => exportCsv(results)}
                className="flex items-center gap-1.5 text-[11px] font-medium text-[--text-muted] hover:text-[--text-primary]"
              >
                <Download className="h-3.5 w-3.5" /> Export CSV
              </button>
            )}
          </div>

          <div className="flex-1 overflow-auto bg-[--bg-base]">
            {error ? (
              <div className="m-4 flex items-start gap-3 rounded-xl border border-[--accent-red]/20 bg-[--accent-red]/10 p-4">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-[--accent-red]" />
                <p className="font-mono text-[12px] text-[--accent-red]">{error}</p>
              </div>
            ) : results === null ? (
              <div className="flex h-full items-center justify-center text-sm text-[--text-muted]">
                Run a query to see results
              </div>
            ) : results.length === 0 ? (
              <div className="flex h-full items-center justify-center text-sm text-[--text-muted]">
                Query returned no rows.
              </div>
            ) : (
              <table className="w-full text-left text-[12px]">
                <thead className="sticky top-0 z-10 border-b border-[--border] bg-[--bg-surface] shadow-sm">
                  <tr>
                    {columns.map(key => (
                      <th key={key} className="px-4 py-2 font-mono font-medium text-[--text-primary]">
                        <div className="flex items-center gap-2">
                          {key}
                          <Badge variant="muted" className="px-1 py-0 text-[8px]">
                            {typeof results[0][key] === 'number' ? 'NUM' : 'STR'}
                          </Badge>
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[--border-subtle]">
                  {results.map((row, i) => (
                    <tr key={i} className="transition-colors hover:bg-[--bg-elevated] even:bg-[--bg-surface]/30">
                      {columns.map((col, j) => (
                        <td key={j} className="px-4 py-2 font-mono text-[--text-muted]">
                          {String(row[col] ?? '')}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {results !== null && !error && (
            <div className="flex shrink-0 items-center gap-4 border-t border-[--border] bg-[--bg-surface] px-4 py-2 font-mono text-[10px] text-[--text-dim]">
              <span>{results.length} rows</span>
              {elapsedMs !== null && (
                <>
                  <span className="h-3 w-px bg-[--border]" />
                  <span>Execution time: {(elapsedMs / 1000).toFixed(2)}s</span>
                </>
              )}
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
