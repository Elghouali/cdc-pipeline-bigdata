import { useState } from 'react';
import CodeMirror from '@uiw/react-codemirror';
import { sql } from '@codemirror/lang-sql';
import { Play, Download, History, Database, ChevronRight, ChevronDown, Table as TableIcon, Columns } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';

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

export function QueryPage() {
  const [query, setQuery] = useState('SELECT\n  order_id,\n  amount,\n  status,\n  created_at\nFROM silver.orders\nWHERE amount > 1000\nORDER BY created_at DESC\nLIMIT 100;');
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState<any[] | null>(null);
  
  // Tree state
  const [expandedLayers, setExpandedLayers] = useState<Record<string, boolean>>({'Silver': true});
  const [expandedTables, setExpandedTables] = useState<Record<string, boolean>>({'orders': true});

  function handleRun() {
    setRunning(true);
    setTimeout(() => {
      setResults([
        { order_id: 'ORD-90421', amount: 1420.50, status: 'COMPLETED', created_at: '2023-10-24 14:22:01' },
        { order_id: 'ORD-90422', amount: 2100.00, status: 'PENDING', created_at: '2023-10-24 14:25:12' },
        { order_id: 'ORD-90423', amount: 1050.25, status: 'COMPLETED', created_at: '2023-10-24 14:30:45' },
      ]);
      setRunning(false);
    }, 800);
  }

  const toggleLayer = (l: string) => setExpandedLayers(prev => ({ ...prev, [l]: !prev[l] }));
  const toggleTable = (t: string) => setExpandedTables(prev => ({ ...prev, [t]: !prev[t] }));

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
                {expandedLayers[layer.layer] ? <ChevronDown className="h-3.5 w-3.5 text-[--text-dim]" /> : <ChevronRight className="h-3.5 w-3.5 text-[--text-dim]" />}
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
                        {expandedTables[table.name] ? <ChevronDown className="h-3.5 w-3.5 text-[--text-dim]" /> : <ChevronRight className="h-3.5 w-3.5 text-[--text-dim]" />}
                        <TableIcon className="h-3.5 w-3.5 text-[--text-muted]" />
                        <span className="text-[13px] text-[--text-muted] hover:text-[--text-primary]">{table.name}</span>
                      </button>
                      
                      {expandedTables[table.name] && (
                        <div className="ml-5 mt-1 space-y-1">
                          {table.columns.map(col => (
                            <div key={col} className="flex items-center gap-1.5 rounded p-1 px-2 text-[12px] text-[--text-dim] transition-colors hover:bg-[--bg-elevated] hover:text-[--text-muted]">
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
              onClick={handleRun}
              disabled={running}
              className="flex items-center gap-1.5 rounded bg-[--accent-cyan] px-3 py-1.5 text-sm font-semibold text-[--bg-base] transition-transform active:scale-95 disabled:opacity-50"
            >
              <Play className="h-4 w-4" fill="currentColor" />
              {running ? 'Running...' : 'Run Query'}
            </button>
            <span className="text-[10px] font-mono text-[--text-dim]">Ctrl + Enter</span>
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
            basicSetup={{
              lineNumbers: true,
              highlightActiveLineGutter: true,
              foldGutter: true,
            }}
            className="text-[13px] font-mono"
            style={{
              '--cm-backgroundColor': 'var(--bg-surface)',
            } as any}
          />
        </div>

        {/* Results */}
        <div className="flex flex-1 flex-col overflow-hidden">
          <div className="flex shrink-0 items-center justify-between border-b border-[--border] bg-[--bg-elevated] px-4 py-2">
            <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[--text-dim]">Results</p>
            {results && (
              <button className="flex items-center gap-1.5 text-[11px] font-medium text-[--text-muted] hover:text-[--text-primary]">
                <Download className="h-3.5 w-3.5" /> Export CSV
              </button>
            )}
          </div>
          
          <div className="flex-1 overflow-auto bg-[--bg-base]">
            {!results ? (
              <div className="flex h-full items-center justify-center text-sm text-[--text-muted]">
                Run a query to see results
              </div>
            ) : (
              <table className="w-full text-left text-[12px]">
                <thead className="sticky top-0 bg-[--bg-surface] z-10 shadow-sm border-b border-[--border]">
                  <tr>
                    {Object.keys(results[0]).map(key => (
                      <th key={key} className="px-4 py-2 font-mono font-medium text-[--text-primary]">
                        <div className="flex items-center gap-2">
                          {key}
                          <Badge variant="muted" className="text-[8px] px-1 py-0">{typeof results[0][key] === 'number' ? 'NUM' : 'STR'}</Badge>
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[--border-subtle]">
                  {results.map((row, i) => (
                    <tr key={i} className="transition-colors hover:bg-[--bg-elevated] even:bg-[--bg-surface]/30">
                      {Object.values(row).map((val: any, j) => (
                        <td key={j} className="px-4 py-2 font-mono text-[--text-muted]">
                          {val}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
          
          {results && (
            <div className="flex shrink-0 items-center gap-4 border-t border-[--border] bg-[--bg-surface] px-4 py-2 font-mono text-[10px] text-[--text-dim]">
              <span>{results.length} rows</span>
              <span className="h-3 w-px bg-[--border]" />
              <span>Execution time: 0.82s</span>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
