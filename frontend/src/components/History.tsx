import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { HistoryItem } from '../types';
import { Clock, RotateCw, Database } from 'lucide-react';

interface HistoryProps {
  onRerun: (runId: string) => void;
}

const History: React.FC<HistoryProps> = ({ onRerun }) => {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadHistory = async () => {
      try {
        const res = await api.getHistory();
        setHistory(res);
      } catch (err) {
        console.error('Failed to load history', err);
      } finally {
        setLoading(false);
      }
    };
    loadHistory();
  }, []);

  if (loading) {
    return <div className="flex h-full items-center justify-center text-slate-400">Loading history...</div>;
  }

  if (history.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center space-y-4 text-slate-400">
        <Database className="h-12 w-12 opacity-50" />
        <p>No extraction history found.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <h2 className="text-2xl font-bold">Extraction History</h2>
      
      <div className="space-y-4">
        {history.map((item) => (
          <div key={item.workflow.id} className="rounded-xl border border-border bg-surface p-6">
            <div className="mb-4">
              <h3 className="text-lg font-medium text-slate-200" title={item.workflow.prompt}>
                "{item.workflow.prompt.length > 80 ? item.workflow.prompt.slice(0, 80) + '...' : item.workflow.prompt}"
              </h3>
              <div className="mt-1 flex items-center gap-2 text-sm text-slate-500">
                <Clock className="h-4 w-4" />
                {new Date(item.workflow.created_at).toLocaleString()}
              </div>
            </div>

            <div className="space-y-3">
              {item.runs.map((run) => (
                <div key={run.run_id} className="flex items-center justify-between rounded-lg bg-[#0f1117] p-4">
                  <div className="flex items-center gap-4">
                    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize
                      ${run.status === 'completed' ? 'bg-green-500/10 text-green-400' : 
                        run.status === 'failed' ? 'bg-red-500/10 text-red-400' : 
                        'bg-blue-500/10 text-blue-400'}`}
                    >
                      {run.status}
                    </span>
                    <span className="text-sm text-slate-300">{run.record_count} records</span>
                  </div>
                  
                  <button
                    onClick={() => onRerun(run.run_id)}
                    className="flex items-center gap-2 text-sm text-indigo-400 transition-colors hover:text-indigo-300"
                  >
                    <RotateCw className="h-4 w-4" /> View / Rerun
                  </button>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default History;
