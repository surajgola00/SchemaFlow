import React, { useEffect, useState } from 'react';
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
  useReactTable,
  getFilteredRowModel,
} from '@tanstack/react-table';
import { Download, Search, ChevronLeft, ChevronRight } from 'lucide-react';
import { api } from '../api/client';
import { ExtractedRecord } from '../types';
import ProvenanceDrawer from './ProvenanceDrawer';

interface DataGridProps {
  runId: string;
}

const columnHelper = createColumnHelper<ExtractedRecord>();

const DataGrid: React.FC<DataGridProps> = ({ runId }) => {
  const [data, setData] = useState<ExtractedRecord[]>([]);
  const [globalFilter, setGlobalFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [selectedRecord, setSelectedRecord] = useState<ExtractedRecord | null>(null);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        const res = await api.getRecords(runId);
        setData(res.records || []);
      } catch (err) {
        console.error('Failed to load records', err);
      } finally {
        setLoading(false);
      }
    };
    if (runId) loadData();
  }, [runId]);

  const dynamicColumns = React.useMemo(() => {
    if (data.length === 0) return [];
    
    const keys = Object.keys(data[0].data);
    const cols = keys.map(key => 
      columnHelper.accessor(row => row.data[key], {
        id: key,
        header: () => <span className="capitalize">{key.replace(/_/g, ' ')}</span>,
        cell: info => <div className="truncate max-w-[200px]" title={String(info.getValue())}>{String(info.getValue())}</div>
      })
    );

    return [
      ...cols,
      columnHelper.accessor('confidence_score', {
        header: 'Confidence',
        cell: info => {
          const score = info.getValue();
          let color = 'bg-red-500/20 text-red-400';
          if (score > 0.9) color = 'bg-green-500/20 text-green-400';
          else if (score > 0.7) color = 'bg-amber-500/20 text-amber-400';
          
          return (
            <span className={`px-2 py-1 rounded text-xs font-medium ${color}`}>
              {(score * 100).toFixed(0)}%
            </span>
          );
        }
      }),
      columnHelper.accessor('is_duplicate', {
        header: 'Unique',
        cell: info => (
          <span className={`px-2 py-1 rounded text-xs font-medium ${info.getValue() ? 'bg-slate-700 text-slate-300' : 'bg-indigo-500/20 text-indigo-400'}`}>
            {info.getValue() ? 'Duplicate' : 'Yes'}
          </span>
        )
      })
    ];
  }, [data]);

  const table = useReactTable({
    data,
    columns: dynamicColumns,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    state: {
      globalFilter,
    },
    onGlobalFilterChange: setGlobalFilter,
  });

  const handleExport = (format: 'csv' | 'json') => {
    window.open(api.exportUrl(runId, format), '_blank');
  };

  if (loading) {
    return <div className="flex h-full items-center justify-center text-slate-400">Loading data...</div>;
  }

  return (
    <div className="flex h-full flex-col space-y-4">
      <div className="flex items-center justify-between">
        <div className="relative w-64">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            value={globalFilter ?? ''}
            onChange={e => setGlobalFilter(e.target.value)}
            className="w-full rounded-lg border border-border bg-surface py-2 pl-9 pr-4 text-sm text-slate-100 placeholder:text-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            placeholder="Search records..."
          />
        </div>
        
        <div className="flex gap-2">
          <button
            onClick={() => handleExport('csv')}
            className="flex items-center gap-2 rounded-lg border border-border bg-surface px-4 py-2 text-sm font-medium text-slate-300 transition-colors hover:bg-slate-800"
          >
            <Download className="h-4 w-4" /> CSV
          </button>
          <button
            onClick={() => handleExport('json')}
            className="flex items-center gap-2 rounded-lg border border-border bg-surface px-4 py-2 text-sm font-medium text-slate-300 transition-colors hover:bg-slate-800"
          >
            <Download className="h-4 w-4" /> JSON
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto rounded-xl border border-border bg-surface">
        <table className="w-full text-left text-sm text-slate-300">
          <thead className="bg-[#0f1117] text-xs uppercase text-slate-400 sticky top-0">
            {table.getHeaderGroups().map(headerGroup => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map(header => (
                  <th key={header.id} className="px-6 py-4 font-semibold border-b border-border">
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map(row => (
              <tr 
                key={row.id} 
                onClick={() => setSelectedRecord(row.original)}
                className="border-b border-border transition-colors hover:bg-slate-800/50 cursor-pointer"
              >
                {row.getVisibleCells().map(cell => (
                  <td key={cell.id} className="px-6 py-4">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between border-t border-border pt-4">
        <div className="text-sm text-slate-400">
          Showing {table.getRowModel().rows.length} of {data.length} records
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
            className="rounded-lg p-2 text-slate-400 hover:bg-surface disabled:opacity-50"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
          <span className="text-sm text-slate-300">
            Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount() || 1}
          </span>
          <button
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
            className="rounded-lg p-2 text-slate-400 hover:bg-surface disabled:opacity-50"
          >
            <ChevronRight className="h-5 w-5" />
          </button>
        </div>
      </div>

      <ProvenanceDrawer 
        record={selectedRecord} 
        onClose={() => setSelectedRecord(null)} 
      />
    </div>
  );
};

export default DataGrid;
