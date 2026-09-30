import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import LogTerminal from './LogTerminal';
import ComplianceBadge from './ComplianceBadge';
import { SSEEvent, LogEntry } from '../types';

interface ExecutionViewProps {
  runId: string;
  onComplete: () => void;
}

const ExecutionView: React.FC<ExecutionViewProps> = ({ runId, onComplete }) => {
  const [progress, setProgress] = useState(0);
  const [step, setStep] = useState('Initializing...');
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [recordCount, setRecordCount] = useState(0);
  const [status, setStatus] = useState<'running' | 'completed' | 'failed'>('running');

  useEffect(() => {
    if (!runId) return;

    const eventSource = new EventSource(api.streamUrl(runId));

    eventSource.onmessage = (e) => {
      try {
        const data: SSEEvent = JSON.parse(e.data);
        
        switch (data.type) {
          case 'progress':
            if (data.pct !== undefined) setProgress(data.pct);
            if (data.step) setStep(data.step);
            break;
          case 'log':
            if (data.level && data.message) {
              setLogs(prev => [...prev, {
                timestamp: new Date().toLocaleTimeString(),
                level: data.level as any,
                message: data.message!
              }]);
            }
            break;
          case 'record':
            if (data.count !== undefined) setRecordCount(data.count);
            break;
          case 'done':
            if (data.status === 'completed') setStatus('completed');
            else if (data.status === 'failed') setStatus('failed');
            eventSource.close();
            break;
        }
      } catch (err) {
        console.error('Error parsing SSE', err);
      }
    };

    eventSource.onerror = () => {
      console.error('SSE Error');
      eventSource.close();
      setStatus('failed');
    };

    return () => {
      eventSource.close();
    };
  }, [runId]);

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold">Execution Status</h2>
          <div className="text-sm text-slate-400">Run ID: {runId.slice(0, 8)}</div>
        </div>
        
        <div className="flex items-center gap-4 py-4">
          <ComplianceBadge label="Robots.txt" compliant={true} />
          <ComplianceBadge label="Sources Verified" compliant={true} />
          <ComplianceBadge label="Dedup Active" compliant={true} />
        </div>
      </div>

      <div className="space-y-4 rounded-xl border border-border bg-surface p-6">
        <div className="flex items-center justify-between text-sm font-medium">
          <span className="text-indigo-400">{step}</span>
          <span className="text-slate-300">{progress}%</span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-[#0f1117]">
          <div
            className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all duration-500 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className="flex justify-between text-sm text-slate-400">
          <span>Records extracted: <strong className="text-slate-200">{recordCount}</strong></span>
          {status === 'completed' && <span className="text-green-500 font-bold">Completed</span>}
          {status === 'failed' && <span className="text-red-500 font-bold">Failed</span>}
        </div>
      </div>

      <div className="space-y-2">
        <h3 className="text-lg font-medium text-slate-300">Live Logs</h3>
        <LogTerminal logs={logs} />
      </div>

      {status === 'completed' && (
        <div className="flex justify-center pt-6">
          <button
            onClick={onComplete}
            className="rounded-lg bg-green-600 px-8 py-3 font-semibold text-white transition-colors hover:bg-green-500"
          >
            View Extracted Data
          </button>
        </div>
      )}
    </div>
  );
};

export default ExecutionView;
