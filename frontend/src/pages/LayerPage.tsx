import { useEffect, useState } from 'react';
import { Database, Table, X } from 'lucide-react';
import { fetchMetrics } from '@/lib/api';
import type { Layer, MetricsResponse } from '@/types/api';
import { formatNumber } from '@/lib/utils';
import { Badge } from '@/components/ui/Badge';

const LAYER_CFG = {
  bronze: { label: 'Bronze Layer', color: '#B08050', badge: 'bronze' as const },
  silver: { label: 'Silver Layer', color: '#8B949E', badge: 'muted' as const },
  gold:   { label: 'Gold Layer',   color: '#D29922', badge: 'warning' as const },
};

export function LayerPage({ layer }: { layer: Layer }) {
  const cfg = LAYER_CFG[layer];
  const [data, setData] = useState<MetricsResponse | null>(null);
  const [selectedTable, setSelectedTable] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const res = await fetchMetrics(layer);
        if (active) setData(res);
      } catch {
        // Handle error
      }
    }
    void load();
    return () => { active = false; };
  }, [layer]);

  const totalRows = data?.tables.reduce((acc, t) => acc + (t.row_count || 0), 0) || 0;
  const totalSize = '1.2 GB'; // Mock data

  return (
    <div className="page-enter flex h-full">
      {/* Main Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mb-6 flex items-end justify-between">
          <div>
            <div className="mb-2 flex items-center gap-2">
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: cfg.color }} />
              <h1 className="text-2xl font-bold text-[--text-primary]" style={{ color: cfg.color }}>{cfg.label}</h1>
            </div>
            <p className="text-sm text-[--text-muted]">Raw CDC events ingested from Kafka</p>
          </div>
          <div className="flex items-center gap-4 text-right">
            <div>
              <p className="mb-1 text-[10px] font-semibold uppercase tracking-[0.08em] text-[--text-dim]">Total Rows</p>
              <p className="font-mono text-xl font-light text-[--text-primary]">{formatNumber(totalRows)}</p>
            </div>
            <div className="h-8 w-px bg-[--border]" />
            <div>
              <p className="mb-1 text-[10px] font-semibold uppercase tracking-[0.08em] text-[--text-dim]">Storage</p>
              <p className="font-mono text-xl font-light text-[--text-primary]">{totalSize}</p>
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-[--border] bg-[--bg-surface] overflow-hidden">
          <div className="grid grid-cols-[2fr_1fr_1fr_1fr_1fr_1fr] border-b border-[--border] bg-[--bg-elevated] px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.08em] text-[--text-dim]">
            <span>Table Name</span>
            <span>Rows</span>
            <span>Last Updated</span>
            <span>Partitions</span>
            <span>Size</span>
            <span>Status</span>
          </div>
          <div className="divide-y divide-[--border-subtle]">
            {data?.tables.map((t) => (
              <button
                key={t.table}
                onClick={() => setSelectedTable(t.table)}
                className="grid w-full grid-cols-[2fr_1fr_1fr_1fr_1fr_1fr] items-center px-4 py-3 text-left transition-colors hover:bg-[--bg-elevated]"
              >
                <div className="flex items-center gap-2">
                  <Table className="h-4 w-4 text-[--text-dim]" />
                  <span className="font-mono text-[13px] text-[--text-primary]">{t.table}</span>
                </div>
                <span className="font-mono text-[13px] text-[--text-muted]">{formatNumber(t.row_count || 0)}</span>
                <span className="font-mono text-[12px] text-[--text-dim]">just now</span>
                <span className="font-mono text-[13px] text-[--text-muted]">6</span>
                <span className="font-mono text-[13px] text-[--text-muted]">45 MB</span>
                <div><Badge variant="success">HEALTHY</Badge></div>
              </button>
            ))}
            {!data && (
              <div className="p-8 text-center text-sm text-[--text-muted]">Loading tables...</div>
            )}
          </div>
        </div>
      </div>

      {/* Side Drawer */}
      {selectedTable && (
        <div className="w-[400px] shrink-0 border-l border-[--border] bg-[--bg-surface] flex flex-col page-enter">
          <div className="flex items-center justify-between border-b border-[--border] px-6 py-4">
            <div className="flex items-center gap-2">
              <Database className="h-5 w-5 text-[--text-dim]" />
              <h2 className="font-mono text-lg font-semibold text-[--text-primary]">{selectedTable}</h2>
            </div>
            <button onClick={() => setSelectedTable(null)} className="rounded p-1 text-[--text-dim] hover:bg-[--bg-elevated] hover:text-[--text-primary]">
              <X className="h-5 w-5" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            <div>
              <h3 className="mb-4 text-[11px] font-semibold uppercase tracking-[0.08em] text-[--text-dim]">Schema Definition</h3>
              <div className="rounded border border-[--border] bg-[--bg-elevated] overflow-hidden">
                <div className="grid grid-cols-[2fr_1fr_1fr] border-b border-[--border] px-3 py-2 text-[10px] uppercase tracking-[0.08em] text-[--text-dim]">
                  <span>Column</span>
                  <span>Type</span>
                  <span>Nullable</span>
                </div>
                <div className="divide-y divide-[--border-subtle] text-[11px]">
                  {['id', 'customer_id', 'amount', 'status', 'created_at'].map(c => (
                    <div key={c} className="grid grid-cols-[2fr_1fr_1fr] px-3 py-2 font-mono">
                      <span className="text-[--accent-cyan]">{c}</span>
                      <span className="text-[--accent-yellow]">STRING</span>
                      <span className="text-[--text-dim]">{c === 'id' ? 'NO' : 'YES'}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            
            <div>
              <h3 className="mb-4 text-[11px] font-semibold uppercase tracking-[0.08em] text-[--text-dim]">Sample Data</h3>
              <div className="rounded border border-[--border] bg-[--bg-elevated] p-4 text-center text-sm text-[--text-muted]">
                Sample data preview not available
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
