import React, { useEffect, useState, useMemo } from 'react';
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
  useReactTable,
  getFilteredRowModel,
  ColumnFiltersState,
  VisibilityState,
} from '@tanstack/react-table';
import {
  Download,
  Search,
  ChevronLeft,
  ChevronRight,
  FileSpreadsheet,
  FileText,
  Filter,
  CheckCircle2,
  AlertCircle,
  Eye,
  ThumbsUp,
  ThumbsDown,
  Flag,
} from 'lucide-react';
import { api } from '../api/client';
import { ExtractedRecord } from '../types';
import ProvenanceDrawer from './ProvenanceDrawer';
import { toast } from 'sonner';

interface DataGridProps {
  runId: string;
}

const columnHelper = createColumnHelper<ExtractedRecord>();

const DataGrid: React.FC<DataGridProps> = ({ runId }) => {
  const [data, setData] = useState<ExtractedRecord[]>([]);
  const [globalFilter, setGlobalFilter] = useState('');
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});
  const [showColumnMenu, setShowColumnMenu] = useState(false);
  const [showFiltersRow, setShowFiltersRow] = useState(false);
  const [wrongRecordIds, setWrongRecordIds] = useState<Set<string>>(new Set());
  const [minConfidence, setMinConfidence] = useState(0);
  const [verifiedOnly, setVerifiedOnly] = useState(false);
  const [loading, setLoading] = useState(true);
  const [selectedRecord, setSelectedRecord] = useState<ExtractedRecord | null>(null);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        const res = await api.getRecords(runId, 1, 100);
        setData(res.records || []);
      } catch (err) {
        console.error('Failed to load records', err);
        toast.error('Failed to load records.');
      } finally {
        setLoading(false);
      }
    };
    if (runId) loadData();
  }, [runId]);

  const handleFlagWrong = async (e: React.MouseEvent, recordId: string) => {
    e.stopPropagation();
    try {
      await api.submitFeedback(recordId, 'wrong', 'User marked as incorrect in Data Explorer');
      setWrongRecordIds((prev) => new Set([...prev, recordId]));
      toast.success('Marked record as wrong. Excluded from CSV/XLSX/JSON exports.');
    } catch {
      toast.error('Failed to submit feedback.');
    }
  };

  const handleFlagCorrect = async (e: React.MouseEvent, recordId: string) => {
    e.stopPropagation();
    try {
      await api.submitFeedback(recordId, 'correct', 'User verified');
      setWrongRecordIds((prev) => {
        const next = new Set(prev);
        next.delete(recordId);
        return next;
      });
      toast.success('Marked record as verified correct.');
    } catch {
      toast.error('Failed to submit feedback.');
    }
  };

  const filteredData = useMemo(() => {
    return data.filter((row) => {
      const conf = row.confidence ?? row.confidence_score ?? 0;
      if (conf < minConfidence) return false;
      if (verifiedOnly && row.verification_status !== 'verified') return false;
      return true;
    });
  }, [data, minConfidence, verifiedOnly]);

  const dynamicColumns = useMemo(() => {
    if (data.length === 0) return [];

    const keys = Object.keys(data[0].data);
    const dataCols = keys.map((key) =>
      columnHelper.accessor((row) => row.data[key], {
        id: key,
        header: () => <span className="capitalize">{key.replace(/_/g, ' ')}</span>,
        cell: (info) => {
          const val = info.getValue();
          const strVal = val === null || val === undefined ? '—' : String(val);
          return (
            <div className="truncate max-w-[200px]" title={strVal}>
              {strVal}
            </div>
          );
        },
      })
    );

    return [
      ...dataCols,
      columnHelper.accessor((row) => row.confidence ?? row.confidence_score, {
        id: 'confidence',
        header: 'Evidence Score',
        cell: (info) => {
          const score = info.getValue() ?? 0;
          let color = 'bg-red-500';
          let textColor = 'text-red-400';
          if (score >= 0.9) {
            color = 'bg-emerald-500';
            textColor = 'text-emerald-400';
          } else if (score >= 0.7) {
            color = 'bg-amber-500';
            textColor = 'text-amber-400';
          }

          return (
            <div className="flex items-center gap-2">
              <div className="w-16 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                <div className={`h-full ${color}`} style={{ width: `${score * 100}%` }} />
              </div>
              <span className={`text-xs font-mono font-medium ${textColor}`}>
                {(score * 100).toFixed(0)}%
              </span>
            </div>
          );
        },
      }),
      columnHelper.accessor('verification_status', {
        header: 'Grounding',
        cell: (info) => {
          const status = info.getValue() || 'verified';
          if (status === 'verified') {
            return (
              <span className="inline-flex items-center gap-1 rounded bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 text-[11px] font-medium text-emerald-400">
                <CheckCircle2 className="h-3 w-3" /> Verified
              </span>
            );
          }
          if (status === 'partial') {
            return (
              <span className="inline-flex items-center gap-1 rounded bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 text-[11px] font-medium text-amber-400">
                <AlertCircle className="h-3 w-3" /> Partial
              </span>
            );
          }
          return (
            <span className="inline-flex items-center gap-1 rounded bg-red-500/10 border border-red-500/20 px-2 py-0.5 text-[11px] font-medium text-red-400">
              Rejected
            </span>
          );
        },
      }),
      columnHelper.accessor('corroboration_count', {
        header: 'Sources',
        cell: (info) => {
          const count = info.getValue() || 1;
          return (
            <span className="rounded bg-slate-800 border border-slate-700 px-2 py-0.5 text-[11px] font-mono text-slate-300">
              {count} {count > 1 ? 'sources' : 'source'}
            </span>
          );
        },
      }),
      columnHelper.display({
        id: 'actions',
        header: 'Feedback',
        cell: (info) => {
          const recId = info.row.original.id;
          const isWrong = wrongRecordIds.has(recId);
          return (
            <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
              {isWrong ? (
                <span className="inline-flex items-center gap-1 rounded bg-red-950/80 border border-red-800 px-2 py-0.5 text-[10px] text-red-300">
                  <Flag className="h-3 w-3" /> Excluded
                </span>
              ) : (
                <>
                  <button
                    onClick={(e) => handleFlagCorrect(e, recId)}
                    className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-emerald-400 transition-colors"
                    title="Mark correct"
                  >
                    <ThumbsUp className="h-3.5 w-3.5" />
                  </button>
                  <button
                    onClick={(e) => handleFlagWrong(e, recId)}
                    className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-red-400 transition-colors"
                    title="Flag as wrong (excludes from export)"
                  >
                    <ThumbsDown className="h-3.5 w-3.5" />
                  </button>
                </>
              )}
            </div>
          );
        },
      }),
    ];
  }, [data, wrongRecordIds]);

  const table = useReactTable({
    data: filteredData,
    columns: dynamicColumns,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    state: {
      globalFilter,
      columnFilters,
      columnVisibility,
    },
    onGlobalFilterChange: setGlobalFilter,
    onColumnFiltersChange: setColumnFilters,
    onColumnVisibilityChange: setColumnVisibility,
  });

  const handleExport = (format: 'csv' | 'json' | 'xlsx' | 'report') => {
    window.open(api.exportUrl(runId, format), '_blank');
    toast.success(`Exporting as ${format.toUpperCase()}... (wrong records excluded)`);
  };

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center text-slate-400 text-sm">
        Loading dataset and provenance records...
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col space-y-4 p-6 overflow-hidden">
      {/* Search & Export Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative w-64">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              value={globalFilter ?? ''}
              onChange={(e) => setGlobalFilter(e.target.value)}
              className="w-full rounded-lg border border-border bg-surface py-1.5 pl-9 pr-4 text-xs text-slate-100 placeholder:text-slate-500 focus:border-indigo-500 focus:outline-none"
              placeholder="Search across all records..."
            />
          </div>

          {/* Filters */}
          <div className="flex items-center gap-2 text-xs text-slate-300 bg-surface border border-border rounded-lg px-3 py-1.5">
            <Filter className="h-3.5 w-3.5 text-indigo-400" />
            <span>Min Score:</span>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={minConfidence}
              onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
              className="w-20 accent-indigo-500"
            />
            <span className="font-mono text-indigo-400 font-bold">{(minConfidence * 100).toFixed(0)}%</span>
          </div>

          <label className="flex items-center gap-1.5 text-xs text-slate-300 cursor-pointer bg-surface border border-border rounded-lg px-3 py-1.5 hover:border-slate-600">
            <input
              type="checkbox"
              checked={verifiedOnly}
              onChange={(e) => setVerifiedOnly(e.target.checked)}
              className="rounded border-border text-indigo-600 focus:ring-0"
            />
            <span>Verified only</span>
          </label>

          {/* Toggle Column Filters Row */}
          <button
            onClick={() => setShowFiltersRow(!showFiltersRow)}
            className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
              showFiltersRow
                ? 'border-indigo-500 bg-indigo-950/40 text-indigo-300'
                : 'border-border bg-surface text-slate-300 hover:bg-slate-800'
            }`}
          >
            <Filter className="h-3.5 w-3.5" />
            {showFiltersRow ? 'Hide Column Filters' : 'Column Filters'}
          </button>

          {/* Column Visibility Menu */}
          <div className="relative">
            <button
              onClick={() => setShowColumnMenu(!showColumnMenu)}
              className="flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-800"
            >
              <Eye className="h-3.5 w-3.5 text-indigo-400" /> Columns
            </button>
            {showColumnMenu && (
              <div className="absolute left-0 top-full mt-1.5 w-52 rounded-xl border border-slate-700 bg-[#0f1117] p-2 shadow-2xl z-30 space-y-1">
                <div className="text-[11px] font-semibold text-slate-400 px-2 py-1 border-b border-slate-800">
                  Toggle Column Visibility
                </div>
                <div className="max-h-56 overflow-y-auto space-y-1 p-1">
                  {table.getAllLeafColumns().map((col) => (
                    <label
                      key={col.id}
                      className="flex items-center gap-2 px-2 py-1 rounded text-xs text-slate-300 hover:bg-slate-800/60 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={col.getIsVisible()}
                        onChange={col.getToggleVisibilityHandler()}
                        className="rounded border-slate-700 text-indigo-500"
                      />
                      <span className="capitalize truncate">{col.id.replace(/_/g, ' ')}</span>
                    </label>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Export buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => handleExport('csv')}
            className="flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-medium text-slate-300 transition-colors hover:bg-slate-800"
            title="Download CSV (excludes flagged records)"
          >
            <Download className="h-3.5 w-3.5" /> CSV
          </button>
          <button
            onClick={() => handleExport('json')}
            className="flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-medium text-slate-300 transition-colors hover:bg-slate-800"
            title="Download JSON with per-field provenance (excludes flagged records)"
          >
            <Download className="h-3.5 w-3.5" /> JSON
          </button>
          <button
            onClick={() => handleExport('xlsx')}
            className="flex items-center gap-1.5 rounded-lg border border-emerald-800/60 bg-emerald-950/30 px-3 py-1.5 text-xs font-medium text-emerald-300 transition-colors hover:bg-emerald-900/40"
            title="Download Excel Workbook (Data + Provenance + Quality sheets)"
          >
            <FileSpreadsheet className="h-3.5 w-3.5 text-emerald-400" /> XLSX
          </button>
          <button
            onClick={() => handleExport('report')}
            className="flex items-center gap-1.5 rounded-lg border border-indigo-700 bg-indigo-950/40 px-3 py-1.5 text-xs font-medium text-indigo-300 transition-colors hover:bg-indigo-900/50"
            title="View HTML Executive Report"
          >
            <FileText className="h-3.5 w-3.5 text-indigo-400" /> Report
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto rounded-xl border border-border bg-surface shadow-sm">
        <table className="w-full text-left text-xs text-slate-300">
          <thead className="bg-[#0f1117] text-[11px] uppercase tracking-wider text-slate-400 sticky top-0 border-b border-border z-10">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th key={header.id} className="px-5 py-3 font-semibold">
                    {header.isPlaceholder
                      ? null
                      : flexRender(header.column.columnDef.header, header.getContext())}
                  </th>
                ))}
              </tr>
            ))}

            {/* Column Filters Input Row */}
            {showFiltersRow && (
              <tr className="bg-[#08090d] border-b border-slate-800">
                {table.getHeaderGroups()[0]?.headers.map((header) => (
                  <th key={`filter-${header.id}`} className="px-3 py-1.5 font-normal">
                    {header.column.getCanFilter() && header.id !== 'actions' ? (
                      <input
                        type="text"
                        value={(header.column.getFilterValue() as string) ?? ''}
                        onChange={(e) => header.column.setFilterValue(e.target.value)}
                        placeholder={`Filter...`}
                        className="w-full rounded border border-slate-800 bg-[#0f1117] px-2 py-0.5 text-[11px] text-slate-200 placeholder:text-slate-600 focus:border-indigo-500 focus:outline-none"
                        onClick={(e) => e.stopPropagation()}
                      />
                    ) : null}
                  </th>
                ))}
              </tr>
            )}
          </thead>
          <tbody className="divide-y divide-border">
            {table.getRowModel().rows.length === 0 ? (
              <tr>
                <td colSpan={dynamicColumns.length || 1} className="text-center py-12 text-slate-500">
                  No records match current filter criteria.
                </td>
              </tr>
            ) : (
              table.getRowModel().rows.map((row) => (
                <tr
                  key={row.id}
                  onClick={() => setSelectedRecord(row.original)}
                  className="transition-colors hover:bg-slate-800/40 cursor-pointer"
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-5 py-3">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="flex items-center justify-between border-t border-border pt-3 text-xs text-slate-400">
        <div>
          Showing {table.getRowModel().rows.length} of {data.length} records (click any row to inspect source evidence)
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
            className="rounded-lg border border-border p-1.5 text-slate-400 hover:bg-surface disabled:opacity-40"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="text-slate-300">
            Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount() || 1}
          </span>
          <button
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
            className="rounded-lg border border-border p-1.5 text-slate-400 hover:bg-surface disabled:opacity-40"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Provenance Drawer */}
      <ProvenanceDrawer record={selectedRecord} onClose={() => setSelectedRecord(null)} />
    </div>
  );
};

export default DataGrid;
