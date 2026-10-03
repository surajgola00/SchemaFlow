import React, { useEffect, useState, useCallback } from 'react';
import { api } from '../api/client';
import LogTerminal from './LogTerminal';
import ReactFlowDag, { NodeStatusInfo } from './ReactFlowDag';
import { SSEEvent, LogEntry, SourceDocument, DagNode } from '../types';
import {
  Pause,
  Play,
  XCircle,
  RotateCcw,
  BookmarkCheck,
  ShieldCheck,
  Activity,
  ArrowRight,
  Globe,
  ExternalLink,
  Ban,
  CheckCircle,
  Terminal,
  Network,
} from 'lucide-react';
import { toast } from 'sonner';

interface ExecutionViewProps {
  runId: string;
  onComplete: () => void;
}

interface ComplianceEvent {
  event: string;
  url?: string;
  allowed?: boolean;
  reason?: string;
  status?: number;
}

const ExecutionView: React.FC<ExecutionViewProps> = ({ runId, onComplete }) => {
  const [progress, setProgress] = useState(0);
  const [step, setStep] = useState('Initializing execution...');
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [recordCount, setRecordCount] = useState(0);
  const [pagesFetched, setPagesFetched] = useState(0);
  const [duplicatesMerged, setDuplicatesMerged] = useState(0);
  const [status, setStatus] = useState<'queued' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled'>('running');
  const [complianceEvents, setComplianceEvents] = useState<ComplianceEvent[]>([]);
  const [isDemoSaved, setIsDemoSaved] = useState(false);

  // Live DAG & Sources State
  const [activeTab, setActiveTab] = useState<'dag' | 'logs' | 'sources'>('dag');
  const [dagNodes, setDagNodes] = useState<DagNode[]>([]);
  const [nodeStatuses, setNodeStatuses] = useState<Record<string, NodeStatusInfo>>({});
  const [sources, setSources] = useState<SourceDocument[]>([]);
  const [sourceFilter, setSourceFilter] = useState<'all' | 'fetched' | 'blocked'>('all');

  const fetchSources = useCallback(async () => {
    if (!runId) return;
    try {
      const docs = await api.getRunSources(runId);
      setSources(docs);
    } catch {
      // Ignored if run is just starting
    }
  }, [runId]);

  // Load initial run details, DAG spec, and node states
  useEffect(() => {
    if (!runId) return;

    api.getRun(runId).then((r: any) => {
      if (r.spec?.dag && r.spec.dag.length > 0) {
        setDagNodes(r.spec.dag);
      } else if (r.dag && r.dag.length > 0) {
        setDagNodes(r.dag);
      }
    }).catch(console.error);

    api.getRunNodes(runId).then((nodes) => {
      const statuses: Record<string, NodeStatusInfo> = {};
      nodes.forEach((n) => {
        statuses[n.node_id] = {
          status: n.status as any,
          items_in: n.items_in,
          items_out: n.items_out,
          error: n.error,
        };
      });
      setNodeStatuses(statuses);
    }).catch(console.error);

    fetchSources();
  }, [runId, fetchSources]);

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
              setLogs((prev) => [
                ...prev,
                {
                  timestamp: data.timestamp || new Date().toLocaleTimeString(),
                  level: data.level as 'INFO' | 'SUCCESS' | 'WARNING' | 'ERROR',
                  message: data.message!,
                  node_id: data.node_id,
                },
              ]);
            }
            break;
          case 'record':
            if (data.count !== undefined) setRecordCount(data.count);
            break;
          case 'compliance':
            if (data.data) {
              setComplianceEvents((prev) => [data.data as unknown as ComplianceEvent, ...prev.slice(0, 15)]);
            }
            break;
          case 'node_started':
            if (data.node_id) {
              setNodeStatuses((prev) => ({
                ...prev,
                [data.node_id!]: {
                  ...prev[data.node_id!],
                  status: 'running',
                },
              }));
            }
            break;
          case 'node_finished':
            if (data.node_id) {
              const nodeStatus = (data.data?.status as any) || 'succeeded';
              const itemsIn = data.data?.items_in !== undefined ? Number(data.data.items_in) : undefined;
              const itemsOut = data.data?.items_out !== undefined ? Number(data.data.items_out) : undefined;
              const errorMsg = data.data?.error ? String(data.data.error) : null;
              setNodeStatuses((prev) => ({
                ...prev,
                [data.node_id!]: {
                  status: nodeStatus === 'completed' ? 'succeeded' : nodeStatus,
                  items_in: itemsIn,
                  items_out: itemsOut,
                  error: errorMsg,
                },
              }));

              if (data.node_id === 'fetch' && data.data?.items_out) {
                setPagesFetched(Number(data.data.items_out));
              }
              if (data.node_id === 'dedupe' && data.data?.merged_count) {
                setDuplicatesMerged(Number(data.data.merged_count));
              }
              fetchSources();
            }
            break;
          case 'run_state':
            if (data.status) {
              setStatus(data.status as any);
            }
            break;
          case 'done':
            if (data.status === 'completed') {
              setStatus('completed');
              setProgress(100);
              fetchSources();
              toast.success('Workflow execution completed successfully!');
            } else if (data.status === 'cancelled') {
              setStatus('cancelled');
              toast.info('Workflow execution cancelled.');
            } else {
              setStatus('failed');
              toast.error('Execution encountered errors.');
            }
            eventSource.close();
            break;
        }
      } catch (err) {
        console.error('Error parsing SSE', err);
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [runId]);

  const handlePause = async () => {
    try {
      await api.pauseRun(runId);
      setStatus('paused');
      toast.info('Execution paused.');
    } catch (err: unknown) {
      toast.error('Failed to pause run.');
    }
  };

  const handleResume = async () => {
    try {
      await api.resumeRun(runId);
      setStatus('running');
      toast.success('Execution resumed.');
    } catch (err: unknown) {
      toast.error('Failed to resume run.');
    }
  };

  const handleCancel = async () => {
    try {
      await api.cancelRun(runId);
      setStatus('cancelled');
      toast.warning('Execution cancelled.');
    } catch (err: unknown) {
      toast.error('Failed to cancel run.');
    }
  };

  const handleRetry = async () => {
    try {
      const res = await api.retryFailed(runId);
      setStatus('running');
      toast.info(`Retrying ${res.retried_nodes} failed nodes...`);
    } catch (err: unknown) {
      toast.error('Failed to retry run.');
    }
  };

  const handleSaveDemo = async () => {
    try {
      const res = await api.saveAsDemo(runId);
      setIsDemoSaved(true);
      toast.success(`Saved run as demo fixture (${res.fixture_id})`);
    } catch (err: unknown) {
      toast.error('Failed to save fixture.');
    }
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6 overflow-y-auto">
      {/* Header & Control Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-2xl font-bold text-white flex items-center gap-2">
              <Activity className="h-6 w-6 text-indigo-400" /> Execution Monitor
            </h2>
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wider ${
                status === 'completed'
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  : status === 'paused'
                  ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                  : status === 'cancelled'
                  ? 'bg-slate-700 text-slate-300'
                  : status === 'failed'
                  ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                  : 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 animate-pulse'
              }`}
            >
              {status}
            </span>
          </div>
          <div className="text-xs text-slate-400 mt-1">Run ID: <span className="font-mono text-slate-300">{runId}</span></div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          {status === 'running' && (
            <button
              onClick={handlePause}
              className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-medium text-amber-300 hover:bg-slate-700 transition-colors"
            >
              <Pause className="h-3.5 w-3.5" /> Pause
            </button>
          )}

          {status === 'paused' && (
            <button
              onClick={handleResume}
              className="flex items-center gap-1.5 rounded-lg border border-emerald-700/50 bg-emerald-900/30 px-3 py-1.5 text-xs font-medium text-emerald-300 hover:bg-emerald-900/50 transition-colors"
            >
              <Play className="h-3.5 w-3.5" /> Resume
            </button>
          )}

          {(status === 'running' || status === 'paused') && (
            <button
              onClick={handleCancel}
              className="flex items-center gap-1.5 rounded-lg border border-red-800/50 bg-red-950/30 px-3 py-1.5 text-xs font-medium text-red-300 hover:bg-red-900/50 transition-colors"
            >
              <XCircle className="h-3.5 w-3.5" /> Cancel
            </button>
          )}

          {(status === 'failed' || status === 'cancelled') && (
            <button
              onClick={handleRetry}
              className="flex items-center gap-1.5 rounded-lg border border-indigo-700 bg-indigo-900/30 px-3 py-1.5 text-xs font-medium text-indigo-300 hover:bg-indigo-900/50 transition-colors"
            >
              <RotateCcw className="h-3.5 w-3.5" /> Retry Failed
            </button>
          )}

          {status === 'completed' && (
            <button
              onClick={handleSaveDemo}
              disabled={isDemoSaved}
              className="flex items-center gap-1.5 rounded-lg border border-purple-700 bg-purple-900/30 px-3 py-1.5 text-xs font-medium text-purple-300 hover:bg-purple-900/50 transition-colors disabled:opacity-50"
            >
              <BookmarkCheck className="h-3.5 w-3.5" /> {isDemoSaved ? 'Saved as Demo' : 'Save as Demo Fixture'}
            </button>
          )}
        </div>
      </div>

      {/* Progress Card & Live Counters */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="rounded-xl border border-border bg-surface p-4">
          <div className="text-xs text-slate-400">Pages Fetched</div>
          <div className="text-2xl font-bold text-white mt-1">{pagesFetched}</div>
          <div className="text-[11px] text-emerald-400 mt-1 flex items-center gap-1">
            <ShieldCheck className="h-3 w-3" /> robots.txt verified
          </div>
        </div>

        <div className="rounded-xl border border-border bg-surface p-4">
          <div className="text-xs text-slate-400">Verified Records</div>
          <div className="text-2xl font-bold text-indigo-400 mt-1">{recordCount}</div>
          <div className="text-[11px] text-slate-400 mt-1">Grounding quotes checked</div>
        </div>

        <div className="rounded-xl border border-border bg-surface p-4">
          <div className="text-xs text-slate-400">Duplicates Merged</div>
          <div className="text-2xl font-bold text-purple-400 mt-1">{duplicatesMerged}</div>
          <div className="text-[11px] text-slate-400 mt-1">Exact + URL + Fuzzy</div>
        </div>

        <div className="rounded-xl border border-border bg-surface p-4">
          <div className="text-xs text-slate-400">Pipeline Stage</div>
          <div className="text-sm font-semibold text-white mt-2 truncate" title={step}>{step}</div>
          <div className="text-[11px] text-indigo-400 mt-1 font-mono">{progress}% Complete</div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="space-y-2 rounded-xl border border-border bg-surface p-4">
        <div className="flex justify-between text-xs text-slate-300">
          <span>{step}</span>
          <span className="font-mono font-bold text-indigo-400">{progress}%</span>
        </div>
        <div className="h-2.5 w-full overflow-hidden rounded-full bg-[#0f1117]">
          <div
            className="h-full bg-gradient-to-r from-indigo-500 via-purple-500 to-emerald-500 transition-all duration-500 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Live Compliance Log Banner */}
      {complianceEvents.length > 0 && (
        <div className="rounded-xl border border-border bg-[#0f1117] p-3 text-xs space-y-1">
          <div className="text-slate-400 font-semibold flex items-center gap-1.5 text-[11px] uppercase tracking-wider">
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" /> Live Compliance Checks
          </div>
          <div className="flex flex-wrap gap-2 pt-1 max-h-16 overflow-y-auto">
            {complianceEvents.map((c, i) => (
              <span
                key={i}
                className={`rounded px-2 py-0.5 text-[11px] font-mono border ${
                  c.event === 'robots_check' && c.allowed
                    ? 'border-emerald-800 bg-emerald-950/40 text-emerald-300'
                    : 'border-amber-800 bg-amber-950/40 text-amber-300'
                }`}
              >
                {c.event === 'robots_check' ? `robots.txt: ${c.url?.slice(0, 30)}... ✓` : `Blocked: ${c.url?.slice(0, 25)}`}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Tab Navigation: DAG / Logs / Sources */}
      <div className="space-y-4">
        <div className="flex items-center justify-between border-b border-border pb-2">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveTab('dag')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                activeTab === 'dag'
                  ? 'bg-indigo-600/30 text-indigo-300 border border-indigo-500/50'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <Network className="h-3.5 w-3.5 text-indigo-400" />
              Pipeline DAG
              {dagNodes.length > 0 && (
                <span className="ml-1 rounded-full bg-slate-800 px-1.5 py-0.2 text-[10px] text-slate-300">
                  {dagNodes.length}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab('logs')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                activeTab === 'logs'
                  ? 'bg-indigo-600/30 text-indigo-300 border border-indigo-500/50'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <Terminal className="h-3.5 w-3.5 text-purple-400" />
              Terminal Logs
              <span className="ml-1 rounded-full bg-slate-800 px-1.5 py-0.2 text-[10px] text-slate-300">
                {logs.length}
              </span>
            </button>

            <button
              onClick={() => setActiveTab('sources')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                activeTab === 'sources'
                  ? 'bg-indigo-600/30 text-indigo-300 border border-indigo-500/50'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <Globe className="h-3.5 w-3.5 text-sky-400" />
              Sources (Used & Blocked)
              <span className="ml-1 rounded-full bg-slate-800 px-1.5 py-0.2 text-[10px] text-slate-300">
                {sources.length}
              </span>
            </button>
          </div>

          <div className="text-xs text-slate-400">
            {activeTab === 'dag' && 'Live node status & item stream'}
            {activeTab === 'logs' && `${logs.length} structured log entries`}
            {activeTab === 'sources' && `${sources.filter(s => s.status === 'fetched').length} fetched, ${sources.filter(s => s.status !== 'fetched').length} blocked`}
          </div>
        </div>

        {/* Tab 1: Live ReactFlow DAG */}
        {activeTab === 'dag' && (
          <div className="space-y-3">
            <ReactFlowDag
              dagNodes={dagNodes.length > 0 ? dagNodes : undefined}
              nodeStatuses={nodeStatuses}
              interactive={true}
              height={320}
            />
            {/* Quick mini-legend */}
            <div className="flex flex-wrap items-center justify-between text-[11px] text-slate-400 px-2">
              <div className="flex items-center gap-4">
                <span className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-slate-500" /> Pending
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-indigo-500 animate-pulse" /> Running
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-emerald-500" /> Succeeded
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-red-500" /> Failed
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-slate-600" /> Skipped
                </span>
              </div>
              <span className="text-slate-500">Pan & Zoom enabled • Click & drag canvas</span>
            </div>
          </div>
        )}

        {/* Tab 2: Terminal Logs */}
        {activeTab === 'logs' && (
          <div className="space-y-2">
            <LogTerminal logs={logs} />
          </div>
        )}

        {/* Tab 3: Sources Panel (Used & Blocked) */}
        {activeTab === 'sources' && (
          <div className="space-y-4 rounded-xl border border-border bg-[#0f1117] p-4">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setSourceFilter('all')}
                  className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                    sourceFilter === 'all'
                      ? 'bg-slate-700 text-white'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  All ({sources.length})
                </button>
                <button
                  onClick={() => setSourceFilter('fetched')}
                  className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                    sourceFilter === 'fetched'
                      ? 'bg-emerald-900/50 text-emerald-300 border border-emerald-700/50'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Permitted & Fetched ({sources.filter((s) => s.status === 'fetched').length})
                </button>
                <button
                  onClick={() => setSourceFilter('blocked')}
                  className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                    sourceFilter === 'blocked'
                      ? 'bg-amber-900/50 text-amber-300 border border-amber-700/50'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Blocked / Failed ({sources.filter((s) => s.status !== 'fetched').length})
                </button>
              </div>
              <div className="text-[11px] text-slate-500">
                Ethical scraping policy: Strict robots.txt compliance & SSRF enforcement
              </div>
            </div>

            {sources.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-500">
                <Globe className="h-8 w-8 mx-auto mb-2 text-slate-600 animate-pulse" />
                Sources discovery in progress or pending run initiation...
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-slate-800 text-[11px] uppercase tracking-wider text-slate-400">
                    <tr>
                      <th className="p-2.5">Status</th>
                      <th className="p-2.5">Source URL</th>
                      <th className="p-2.5">Connector</th>
                      <th className="p-2.5">HTTP Status</th>
                      <th className="p-2.5">Reason / Notes</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                    {sources
                      .filter((s) => {
                        if (sourceFilter === 'fetched') return s.status === 'fetched';
                        if (sourceFilter === 'blocked') return s.status !== 'fetched';
                        return true;
                      })
                      .map((src) => {
                        const isFetched = src.status === 'fetched';
                        return (
                          <tr key={src.id} className="hover:bg-slate-800/30">
                            <td className="p-2.5 whitespace-nowrap">
                              {isFetched ? (
                                <span className="inline-flex items-center gap-1 rounded bg-emerald-950/60 border border-emerald-800 px-2 py-0.5 text-emerald-300 text-[10px]">
                                  <CheckCircle className="h-3 w-3" /> Fetched
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 rounded bg-amber-950/60 border border-amber-800 px-2 py-0.5 text-amber-300 text-[10px]">
                                  <Ban className="h-3 w-3" /> {src.status.toUpperCase()}
                                </span>
                              )}
                            </td>
                            <td className="p-2.5 max-w-sm truncate text-slate-300">
                              <a
                                href={src.url}
                                target="_blank"
                                rel="noreferrer"
                                className="hover:text-indigo-400 inline-flex items-center gap-1 hover:underline"
                                title={src.url}
                              >
                                {src.url}
                                <ExternalLink className="h-3 w-3 opacity-60" />
                              </a>
                            </td>
                            <td className="p-2.5 whitespace-nowrap">
                              <span className="rounded bg-slate-800 px-2 py-0.5 text-slate-300 text-[10px]">
                                {src.connector || 'web'}
                              </span>
                            </td>
                            <td className="p-2.5 whitespace-nowrap">
                              <span
                                className={`font-semibold ${
                                  src.http_status >= 200 && src.http_status < 300
                                    ? 'text-emerald-400'
                                    : src.http_status === 429
                                    ? 'text-amber-400'
                                    : 'text-red-400'
                                }`}
                              >
                                {src.http_status || '—'}
                              </span>
                            </td>
                            <td className="p-2.5 text-slate-400 max-w-xs truncate" title={src.blocked_reason || (isFetched ? 'Allowed by robots.txt' : '')}>
                              {src.blocked_reason || (isFetched ? 'Allowed by robots.txt' : 'Unknown')}
                            </td>
                          </tr>
                        );
                      })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Completion CTA */}
      {status === 'completed' && (
        <div className="flex justify-center pt-2">
          <button
            onClick={onComplete}
            className="flex items-center gap-2 rounded-lg bg-emerald-600 px-8 py-3 font-bold text-white shadow-lg transition-transform hover:scale-105 text-sm"
          >
            Explore Extracted Dataset <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  );
};

export default ExecutionView;
