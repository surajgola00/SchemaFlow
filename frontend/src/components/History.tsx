import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { HistoryItem, Dataset, DatasetVersion } from '../types';
import {
  Clock,
  Database,
  Copy,
  Search,
  Eye,
  Calendar,
  GitCompare,
  X,
  Check,
  GitCommit,
  ArrowRight,
  RefreshCw,
} from 'lucide-react';
import { toast } from 'sonner';

interface HistoryProps {
  onRerun: (runId: string) => void;
}

interface DiffResult {
  from_version: number;
  to_version: number;
  added: Array<{ key: string; data: Record<string, unknown> }>;
  removed: Array<{ key: string; data: Record<string, unknown> }>;
  changed: Array<{ key: string; field: string; old: unknown; new: unknown }>;
  schema_changed: boolean;
  summary: { added_count: number; removed_count: number; changed_count: number };
}

const History: React.FC<HistoryProps> = ({ onRerun }) => {
  const [activeTab, setActiveTab] = useState<'workflows' | 'datasets'>('workflows');
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  // Schedule Modal State
  const [schedulingWorkflow, setSchedulingWorkflow] = useState<string | null>(null);
  const [cronExpression, setCronExpression] = useState('0 9 * * *');
  const [scheduleLabel, setScheduleLabel] = useState('Daily Morning Run');
  const [isSavingSchedule, setIsSavingSchedule] = useState(false);

  // Dataset Diff State
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
  const [datasetVersions, setDatasetVersions] = useState<DatasetVersion[]>([]);
  const [fromVer, setFromVer] = useState<number>(1);
  const [toVer, setToVer] = useState<number>(2);
  const [diffResult, setDiffResult] = useState<DiffResult | null>(null);
  const [loadingDiff, setLoadingDiff] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [histRes, dsRes] = await Promise.all([
        api.getHistory().catch(() => []),
        api.getDatasets().catch(() => []),
      ]);
      setHistory(histRes || []);
      setDatasets(dsRes || []);
    } catch (err) {
      console.error('Failed to load history or datasets', err);
      toast.error('Failed to load history data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleClone = async (workflowId: string) => {
    try {
      const res = await api.cloneWorkflow(workflowId);
      toast.success(`Workflow cloned successfully (${res.workflow_id.slice(0, 8)})`);
      loadData();
    } catch {
      toast.error('Failed to clone workflow.');
    }
  };

  const handleCreateSchedule = async () => {
    if (!schedulingWorkflow) return;
    setIsSavingSchedule(true);
    try {
      await api.createSchedule({
        workflow_id: schedulingWorkflow,
        cron_expression: cronExpression,
        label: scheduleLabel,
      });
      toast.success(`Schedule registered (${cronExpression})`);
      setSchedulingWorkflow(null);
    } catch {
      toast.error('Failed to create schedule.');
    } finally {
      setIsSavingSchedule(false);
    }
  };

  const handleSelectDataset = async (ds: Dataset) => {
    setSelectedDataset(ds);
    setDiffResult(null);
    try {
      const vers = await api.getDatasetVersions(ds.id);
      setDatasetVersions(vers || []);
      if (vers && vers.length >= 2) {
        setFromVer(vers[0].version_no);
        setToVer(vers[vers.length - 1].version_no);
      } else if (vers && vers.length === 1) {
        setFromVer(vers[0].version_no);
        setToVer(vers[0].version_no);
      }
    } catch {
      toast.error('Failed to load dataset versions.');
    }
  };

  const handleComputeDiff = async () => {
    if (!selectedDataset) return;
    setLoadingDiff(true);
    try {
      const res = await api.getDatasetDiff(selectedDataset.id, fromVer, toVer);
      setDiffResult(res);
      toast.success(`Diff calculated: +${res.summary.added_count} / -${res.summary.removed_count} / ~${res.summary.changed_count}`);
    } catch (err) {
      console.error('Failed to compute diff', err);
      toast.error('Failed to compute dataset diff.');
    } finally {
      setLoadingDiff(false);
    }
  };

  const filteredHistory = history.filter((item) => {
    const text = (item.workflow.title || item.workflow.prompt).toLowerCase();
    return text.includes(searchTerm.toLowerCase());
  });

  const filteredDatasets = datasets.filter((ds) => {
    const text = (ds.title || ds.entity_type || ds.id).toLowerCase();
    return text.includes(searchTerm.toLowerCase());
  });

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center text-slate-400 text-sm">
        Loading execution history & datasets...
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6 overflow-y-auto">
      {/* Header & Sub-Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-4">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <Database className="h-6 w-6 text-indigo-400" /> History & Datasets
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Browse past workflow compilations, dataset version timeline, diffs, and recurring schedules.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border border-border bg-[#0f1117] p-1 text-xs">
            <button
              onClick={() => setActiveTab('workflows')}
              className={`rounded px-3 py-1 font-medium transition-colors ${
                activeTab === 'workflows'
                  ? 'bg-indigo-600 text-white shadow'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Workflows & Runs ({history.length})
            </button>
            <button
              onClick={() => setActiveTab('datasets')}
              className={`rounded px-3 py-1 font-medium transition-colors ${
                activeTab === 'datasets'
                  ? 'bg-indigo-600 text-white shadow'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Datasets & Version Diff ({datasets.length})
            </button>
          </div>

          <div className="relative w-56">
            <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search..."
              className="w-full rounded-lg border border-border bg-surface py-1 pl-8 pr-3 text-xs text-slate-100 placeholder:text-slate-500 focus:border-indigo-500 focus:outline-none"
            />
          </div>
        </div>
      </div>

      {/* Tab 1: Workflows & Runs */}
      {activeTab === 'workflows' && (
        <div className="space-y-4">
          {filteredHistory.length === 0 ? (
            <div className="py-12 text-center text-slate-400 text-sm">
              No workflows found. Launch one from the Studio.
            </div>
          ) : (
            filteredHistory.map((item) => (
              <div key={item.workflow.id} className="rounded-xl border border-border bg-surface p-5 space-y-4 shadow-sm">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-base font-bold text-slate-100">
                        {item.workflow.title || item.workflow.prompt}
                      </h3>
                      {item.workflow.entity_type && (
                        <span className="rounded bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 text-[10px] font-semibold text-indigo-300">
                          {item.workflow.entity_type}
                        </span>
                      )}
                    </div>
                    <div className="mt-1 flex items-center gap-3 text-xs text-slate-500">
                      <span className="flex items-center gap-1">
                        <Clock className="h-3.5 w-3.5" />
                        {new Date(item.workflow.created_at).toLocaleString()}
                      </span>
                      <span>•</span>
                      <span>{item.runs.length} execution {item.runs.length === 1 ? 'run' : 'runs'}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => {
                        setSchedulingWorkflow(item.workflow.id);
                        setScheduleLabel(item.workflow.title || 'Scheduled Pipeline');
                      }}
                      className="flex items-center gap-1.5 rounded-lg border border-border bg-[#0f1117] px-2.5 py-1.5 text-xs font-medium text-slate-300 hover:border-indigo-500 hover:text-indigo-400 transition-colors"
                      title="Set up cron schedule"
                    >
                      <Calendar className="h-3.5 w-3.5 text-purple-400" /> Schedule
                    </button>
                    <button
                      onClick={() => handleClone(item.workflow.id)}
                      className="flex items-center gap-1.5 rounded-lg border border-border bg-[#0f1117] px-2.5 py-1.5 text-xs font-medium text-slate-300 hover:border-indigo-500 hover:text-indigo-400 transition-colors"
                      title="Clone workflow specification"
                    >
                      <Copy className="h-3.5 w-3.5 text-indigo-400" /> Clone
                    </button>
                  </div>
                </div>

                {/* Runs List */}
                <div className="space-y-2">
                  {item.runs.map((run) => (
                    <div
                      key={run.run_id}
                      className="flex items-center justify-between rounded-lg bg-[#0f1117] p-3 text-xs border border-slate-800/60"
                    >
                      <div className="flex items-center gap-3">
                        <span
                          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium capitalize ${
                            run.status === 'completed'
                              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                              : run.status === 'failed'
                              ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                              : run.status === 'paused'
                              ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                              : 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                          }`}
                        >
                          {run.status}
                        </span>
                        <span className="font-semibold text-slate-200">{run.record_count} records</span>
                        <span className="text-slate-500 font-mono text-[11px]">{run.run_id.slice(0, 8)}</span>
                      </div>

                      <button
                        onClick={() => onRerun(run.run_id)}
                        className="flex items-center gap-1.5 font-medium text-indigo-400 hover:text-indigo-300 transition-colors"
                      >
                        <Eye className="h-3.5 w-3.5" /> Inspect Dataset
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Tab 2: Datasets & Version Diff */}
      {activeTab === 'datasets' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Datasets List */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-slate-300">Managed Datasets</h3>
            {filteredDatasets.length === 0 ? (
              <div className="rounded-xl border border-border bg-surface p-6 text-center text-xs text-slate-500">
                No datasets generated yet. Launch a run from Studio.
              </div>
            ) : (
              filteredDatasets.map((ds) => (
                <div
                  key={ds.id}
                  onClick={() => handleSelectDataset(ds)}
                  className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                    selectedDataset?.id === ds.id
                      ? 'border-indigo-500 bg-indigo-950/30 text-white'
                      : 'border-border bg-surface text-slate-300 hover:border-slate-700'
                  }`}
                >
                  <div className="font-semibold text-xs truncate">{ds.title || 'Untitled Dataset'}</div>
                  <div className="text-[11px] text-slate-400 mt-1 flex items-center justify-between">
                    <span>{ds.entity_type || 'Custom Entities'}</span>
                    <span className="font-mono text-indigo-400">
                      {ds.version_count || 1} {ds.version_count === 1 ? 'version' : 'versions'}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Timeline & Diff View */}
          <div className="md:col-span-2 space-y-4">
            {selectedDataset ? (
              <div className="rounded-xl border border-border bg-surface p-5 space-y-5">
                <div>
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    <GitCommit className="h-4 w-4 text-indigo-400" />
                    {selectedDataset.title || 'Dataset'} — Version Timeline
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Dataset ID: <span className="font-mono">{selectedDataset.id.slice(0, 8)}</span>
                  </p>
                </div>

                {/* Timeline */}
                <div className="space-y-2 border-l-2 border-indigo-500/40 pl-4 ml-1">
                  {datasetVersions.map((v) => (
                    <div key={v.id} className="relative pb-2">
                      <div className="absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full bg-indigo-500" />
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-bold text-indigo-300">Version {v.version_no}</span>
                        <span className="text-[11px] text-slate-500">
                          {new Date(v.created_at).toLocaleString()}
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-400 mt-0.5 flex items-center gap-3">
                        <span>{v.record_count} verified records</span>
                        {typeof v.quality_summary?.verified_ratio === 'number' && (
                          <span className="text-emerald-400">
                            {(Number(v.quality_summary.verified_ratio) * 100).toFixed(0)}% verified
                          </span>
                        )}
                        <span className="font-mono text-slate-500">run: {v.run_id.slice(0, 8)}</span>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Version Diff Selector */}
                {datasetVersions.length >= 2 ? (
                  <div className="space-y-3 rounded-xl border border-border bg-[#0f1117] p-4">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
                        <GitCompare className="h-3.5 w-3.5 text-indigo-400" /> Compare Dataset Versions
                      </span>
                      <button
                        onClick={handleComputeDiff}
                        disabled={loadingDiff}
                        className="flex items-center gap-1 rounded bg-indigo-600 px-3 py-1 text-xs font-bold text-white hover:bg-indigo-500 disabled:opacity-50"
                      >
                        {loadingDiff ? <RefreshCw className="h-3 w-3 animate-spin" /> : <GitCompare className="h-3 w-3" />}
                        Compute Diff
                      </button>
                    </div>

                    <div className="flex items-center gap-3 text-xs">
                      <div className="flex-1">
                        <label className="text-[11px] text-slate-400">From Version</label>
                        <select
                          value={fromVer}
                          onChange={(e) => setFromVer(Number(e.target.value))}
                          className="mt-1 w-full rounded border border-border bg-surface px-2.5 py-1 text-slate-200 text-xs"
                        >
                          {datasetVersions.map((v) => (
                            <option key={v.id} value={v.version_no}>
                              v{v.version_no} ({v.record_count} records)
                            </option>
                          ))}
                        </select>
                      </div>

                      <ArrowRight className="h-4 w-4 text-slate-500 mt-5" />

                      <div className="flex-1">
                        <label className="text-[11px] text-slate-400">To Version</label>
                        <select
                          value={toVer}
                          onChange={(e) => setToVer(Number(e.target.value))}
                          className="mt-1 w-full rounded border border-border bg-surface px-2.5 py-1 text-slate-200 text-xs"
                        >
                          {datasetVersions.map((v) => (
                            <option key={v.id} value={v.version_no}>
                              v{v.version_no} ({v.record_count} records)
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>

                    {/* Diff Results Preview */}
                    {diffResult && (
                      <div className="space-y-3 pt-3 border-t border-slate-800">
                        <div className="grid grid-cols-3 gap-2 text-center text-xs">
                          <div className="rounded bg-emerald-950/40 border border-emerald-800/50 p-2">
                            <div className="text-emerald-400 font-bold text-sm">+{diffResult.summary.added_count}</div>
                            <div className="text-[10px] text-slate-400">Added Records</div>
                          </div>
                          <div className="rounded bg-red-950/40 border border-red-800/50 p-2">
                            <div className="text-red-400 font-bold text-sm">-{diffResult.summary.removed_count}</div>
                            <div className="text-[10px] text-slate-400">Removed Records</div>
                          </div>
                          <div className="rounded bg-amber-950/40 border border-amber-800/50 p-2">
                            <div className="text-amber-400 font-bold text-sm">~{diffResult.summary.changed_count}</div>
                            <div className="text-[10px] text-slate-400">Changed Fields</div>
                          </div>
                        </div>

                        {diffResult.changed.length > 0 && (
                          <div className="overflow-x-auto max-h-48">
                            <table className="w-full text-left text-[11px] font-mono">
                              <thead className="text-slate-400 border-b border-slate-800">
                                <tr>
                                  <th className="p-1.5">Key</th>
                                  <th className="p-1.5">Field</th>
                                  <th className="p-1.5 text-red-400">Old Value</th>
                                  <th className="p-1.5 text-emerald-400">New Value</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-slate-800/60">
                                {diffResult.changed.map((c, i) => (
                                  <tr key={i}>
                                    <td className="p-1.5 max-w-[120px] truncate text-slate-300">{c.key}</td>
                                    <td className="p-1.5 text-indigo-300">{c.field}</td>
                                    <td className="p-1.5 text-red-300 max-w-[100px] truncate">{String(c.old)}</td>
                                    <td className="p-1.5 text-emerald-300 max-w-[100px] truncate">{String(c.new)}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="rounded-lg border border-slate-800 bg-[#0f1117] p-4 text-center text-xs text-slate-400">
                    Re-run this workflow to generate Version 2 and view run-to-run diffs.
                  </div>
                )}
              </div>
            ) : (
              <div className="rounded-xl border border-border bg-surface p-12 text-center text-xs text-slate-500">
                Select a dataset on the left to inspect its version timeline and diffs.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Schedule Trigger Modal */}
      {schedulingWorkflow && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-xl border border-border bg-surface p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Calendar className="h-4 w-4 text-indigo-400" /> Schedule Workflow
              </h3>
              <button
                onClick={() => setSchedulingWorkflow(null)}
                className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="text-slate-400">Schedule Label</label>
                <input
                  type="text"
                  value={scheduleLabel}
                  onChange={(e) => setScheduleLabel(e.target.value)}
                  className="mt-1 w-full rounded border border-border bg-[#0f1117] px-3 py-1.5 text-slate-200"
                />
              </div>

              <div>
                <label className="text-slate-400">Cron Expression</label>
                <input
                  type="text"
                  value={cronExpression}
                  onChange={(e) => setCronExpression(e.target.value)}
                  placeholder="0 9 * * *"
                  className="mt-1 w-full font-mono rounded border border-border bg-[#0f1117] px-3 py-1.5 text-indigo-300"
                />
              </div>

              {/* Quick Presets */}
              <div className="flex flex-wrap gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => setCronExpression('0 */6 * * *')}
                  className="rounded bg-slate-800 border border-slate-700 px-2 py-1 text-[11px] text-slate-300 hover:border-indigo-500"
                >
                  Every 6 Hours
                </button>
                <button
                  type="button"
                  onClick={() => setCronExpression('0 9 * * *')}
                  className="rounded bg-slate-800 border border-slate-700 px-2 py-1 text-[11px] text-slate-300 hover:border-indigo-500"
                >
                  Daily at 9 AM
                </button>
                <button
                  type="button"
                  onClick={() => setCronExpression('0 9 * * 1')}
                  className="rounded bg-slate-800 border border-slate-700 px-2 py-1 text-[11px] text-slate-300 hover:border-indigo-500"
                >
                  Weekly Monday
                </button>
              </div>
            </div>

            <div className="flex justify-end gap-2 border-t border-border pt-4">
              <button
                onClick={() => setSchedulingWorkflow(null)}
                className="rounded px-4 py-2 text-xs font-semibold text-slate-400 hover:bg-slate-800"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateSchedule}
                disabled={isSavingSchedule}
                className="flex items-center gap-1.5 rounded bg-indigo-600 px-4 py-2 text-xs font-bold text-white hover:bg-indigo-500 disabled:opacity-50"
              >
                <Check className="h-3.5 w-3.5" /> Save Schedule
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default History;
