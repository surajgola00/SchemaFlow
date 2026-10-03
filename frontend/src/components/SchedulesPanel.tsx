import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { Schedule, HistoryItem } from '../types';
import { Clock, Plus, Trash2, Calendar } from 'lucide-react';
import { toast } from 'sonner';

const PRESET_CRONS = [
  { label: 'Hourly', cron: '0 * * * *' },
  { label: 'Daily (9:00 AM UTC)', cron: '0 9 * * *' },
  { label: 'Weekly (Mondays)', cron: '0 9 * * 1' },
];

const SchedulesPanel: React.FC = () => {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [selectedWorkflowId, setSelectedWorkflowId] = useState('');
  const [cronExpr, setCronExpr] = useState('0 9 * * *');
  const [label, setLabel] = useState('');
  const [loading, setLoading] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [scheds, hist] = await Promise.all([api.getSchedules(), api.getHistory()]);
      setSchedules(scheds || []);
      setHistory(hist || []);
      if (hist && hist.length > 0 && !selectedWorkflowId) {
        setSelectedWorkflowId(hist[0].workflow.id);
      }
    } catch {
      toast.error('Failed to load schedules.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreate = async () => {
    if (!selectedWorkflowId) {
      toast.error('Please select a workflow to schedule.');
      return;
    }
    try {
      await api.createSchedule({
        workflow_id: selectedWorkflowId,
        cron_expression: cronExpr,
        label: label || 'Automated Recurring Crawl',
      });
      toast.success('Schedule created successfully.');
      setLabel('');
      loadData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Invalid cron expression';
      toast.error(msg);
    }
  };

  const handleToggle = async (schedule: Schedule) => {
    try {
      await api.updateSchedule(schedule.id, { enabled: !schedule.enabled });
      toast.success(`Schedule ${!schedule.enabled ? 'enabled' : 'paused'}.`);
      loadData();
    } catch {
      toast.error('Failed to update schedule.');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.deleteSchedule(id);
      toast.success('Schedule removed.');
      loadData();
    } catch {
      toast.error('Failed to delete schedule.');
    }
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6 overflow-y-auto">
      <div>
        <h2 className="text-2xl font-bold text-white flex items-center gap-2">
          <Calendar className="h-6 w-6 text-indigo-400" /> Recurring Collection Schedules
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Automate recurring dataset refreshes and track runs over time using APScheduler.
        </p>
      </div>

      {/* Create Schedule Card */}
      <div className="rounded-xl border border-border bg-surface p-5 space-y-4 shadow-sm">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <Plus className="h-4 w-4 text-indigo-400" /> Create New Schedule
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div>
            <label className="text-slate-400 mb-1 block">Target Workflow</label>
            <select
              value={selectedWorkflowId}
              onChange={(e) => setSelectedWorkflowId(e.target.value)}
              className="w-full rounded-lg border border-border bg-[#0f1117] p-2 text-slate-100 focus:border-indigo-500 focus:outline-none"
            >
              {history.map((h) => (
                <option key={h.workflow.id} value={h.workflow.id}>
                  {h.workflow.title || h.workflow.prompt.slice(0, 45) + '...'}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-slate-400 mb-1 block">Cron Expression</label>
            <input
              type="text"
              value={cronExpr}
              onChange={(e) => setCronExpr(e.target.value)}
              placeholder="e.g. 0 9 * * *"
              className="w-full rounded-lg border border-border bg-[#0f1117] p-2 text-slate-100 font-mono text-xs focus:border-indigo-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="text-slate-400 mb-1 block">Schedule Label</label>
            <input
              type="text"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="e.g. Daily Morning Sync"
              className="w-full rounded-lg border border-border bg-[#0f1117] p-2 text-slate-100 text-xs focus:border-indigo-500 focus:outline-none"
            />
          </div>
        </div>

        {/* Quick Cron Presets */}
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <span className="text-[11px] text-slate-500 font-medium">Presets:</span>
          {PRESET_CRONS.map((p, i) => (
            <button
              key={i}
              onClick={() => setCronExpr(p.cron)}
              className="rounded bg-[#0f1117] border border-border px-2.5 py-1 text-[11px] text-slate-300 hover:border-indigo-500 hover:text-indigo-400"
            >
              {p.label} ({p.cron})
            </button>
          ))}
        </div>

        <div className="flex justify-end pt-2">
          <button
            onClick={handleCreate}
            className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-5 py-2 text-xs font-semibold text-white hover:bg-indigo-500 shadow-sm"
          >
            <Plus className="h-3.5 w-3.5" /> Save Schedule
          </button>
        </div>
      </div>

      {/* Schedules List */}
      <div className="rounded-xl border border-border bg-surface p-5 space-y-4">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <Clock className="h-4 w-4 text-indigo-400" /> Active Schedules ({schedules.length})
        </h3>

        {loading ? (
          <div className="text-xs text-slate-500 py-6 text-center">Loading schedules...</div>
        ) : schedules.length === 0 ? (
          <div className="text-xs text-slate-500 py-8 text-center">No recurring schedules registered yet.</div>
        ) : (
          <div className="divide-y divide-border rounded-lg border border-border bg-[#0f1117]">
            {schedules.map((s) => (
              <div key={s.id} className="flex items-center justify-between p-4 hover:bg-slate-800/30">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-white">{s.label || 'Scheduled Task'}</span>
                    <span
                      className={`rounded px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${
                        s.enabled ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-700 text-slate-400'
                      }`}
                    >
                      {s.enabled ? 'Active' : 'Paused'}
                    </span>
                  </div>
                  <div className="text-xs font-mono text-indigo-400">{s.cron_expression}</div>
                  {s.next_run_at && (
                    <div className="text-[11px] text-slate-500">
                      Next run: {new Date(s.next_run_at).toLocaleString()}
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleToggle(s)}
                    className="rounded-lg border border-border bg-surface px-3 py-1.5 text-xs text-slate-300 hover:text-white"
                  >
                    {s.enabled ? 'Pause' : 'Enable'}
                  </button>
                  <button
                    onClick={() => handleDelete(s.id)}
                    className="p-1.5 text-slate-500 hover:text-red-400"
                    title="Delete schedule"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default SchedulesPanel;
