import {
  Workflow,
  ExecutionRun,
  ExtractedRecord,
  HistoryItem,
  SystemStatus,
  NodeRun,
  QualityReport,
  SourceDocument,
  FieldProvenance,
  Dataset,
  DatasetVersion,
  Schedule,
  WorkflowSpec,
} from '../types';

const BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8000';

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });
  } catch (err: any) {
    if (err instanceof TypeError || err?.name === 'TypeError') {
      throw new Error(`Backend unreachable at ${BASE_URL}. Is the backend server running?`);
    }
    throw err;
  }

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || errorData.message || `Request failed with status ${res.status}`);
  }

  return res.json();
}

export const api = {
  // System status
  systemStatus: (): Promise<SystemStatus> =>
    request<SystemStatus>('/api/v1/system/status'),

  // Workflows
  compileWorkflow: (prompt: string, useMock: boolean = true): Promise<Workflow> =>
    request<Workflow>('/api/v1/compile', {
      method: 'POST',
      body: JSON.stringify({ prompt, use_mock: useMock }),
    }),

  updateWorkflow: (workflowId: string, spec: WorkflowSpec): Promise<{ workflow_id: string; spec: WorkflowSpec }> =>
    request<{ workflow_id: string; spec: WorkflowSpec }>(`/api/v1/workflows/${workflowId}`, {
      method: 'PUT',
      body: JSON.stringify({ spec }),
    }),

  cloneWorkflow: (workflowId: string): Promise<{ workflow_id: string; parent_id: string }> =>
    request<{ workflow_id: string; parent_id: string }>(`/api/v1/workflows/${workflowId}/clone`, {
      method: 'POST',
    }),

  // Runs
  startRun: (
    workflowId: string,
    approvedSchema: unknown[] = [],
    approvedDag: unknown[] = [],
    useMock: boolean = true,
    engineMode: string = 'demo'
  ): Promise<{ run_id: string; status: string }> =>
    request<{ run_id: string; status: string }>('/api/v1/runs/start', {
      method: 'POST',
      body: JSON.stringify({
        workflow_id: workflowId,
        approved_schema: approvedSchema,
        approved_dag: approvedDag,
        use_mock: useMock,
        engine_mode: engineMode,
      }),
    }),

  getRun: (runId: string): Promise<ExecutionRun> =>
    request<ExecutionRun>(`/api/v1/runs/${runId}`),

  pauseRun: (runId: string): Promise<{ run_id: string; state: string }> =>
    request<{ run_id: string; state: string }>(`/api/v1/runs/${runId}/pause`, { method: 'POST' }),

  resumeRun: (runId: string): Promise<{ run_id: string; state: string }> =>
    request<{ run_id: string; state: string }>(`/api/v1/runs/${runId}/resume`, { method: 'POST' }),

  cancelRun: (runId: string): Promise<{ run_id: string; state: string }> =>
    request<{ run_id: string; state: string }>(`/api/v1/runs/${runId}/cancel`, { method: 'POST' }),

  retryFailed: (runId: string): Promise<{ run_id: string; retried_nodes: number }> =>
    request<{ run_id: string; retried_nodes: number }>(`/api/v1/runs/${runId}/retry-failed`, { method: 'POST' }),

  deleteRun: (runId: string): Promise<{ deleted: string }> =>
    request<{ deleted: string }>(`/api/v1/runs/${runId}`, { method: 'DELETE' }),

  saveAsDemo: (runId: string): Promise<{ fixture_id: string; record_count: number }> =>
    request<{ fixture_id: string; record_count: number }>(`/api/v1/runs/${runId}/save-as-demo`, { method: 'POST' }),

  getRunNodes: (runId: string): Promise<NodeRun[]> =>
    request<NodeRun[]>(`/api/v1/runs/${runId}/nodes`),

  getRunQuality: (runId: string): Promise<QualityReport> =>
    request<QualityReport>(`/api/v1/runs/${runId}/quality`),

  getRunSources: (runId: string): Promise<SourceDocument[]> =>
    request<SourceDocument[]>(`/api/v1/runs/${runId}/sources`),

  getRecords: (
    runId: string,
    page: number = 1,
    pageSize: number = 20,
    search?: string,
    minConfidence?: number,
    verifiedOnly?: boolean
  ): Promise<{ total: number; page: number; records: ExtractedRecord[] }> => {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });
    if (search) params.set('search', search);
    if (minConfidence !== undefined) params.set('min_confidence', String(minConfidence));
    if (verifiedOnly) params.set('verified_only', 'true');
    return request<{ total: number; page: number; records: ExtractedRecord[] }>(
      `/api/v1/runs/${runId}/records?${params.toString()}`
    );
  },

  // Record Provenance & Feedback
  getRecordProvenance: (recordId: string): Promise<FieldProvenance[]> =>
    request<FieldProvenance[]>(`/api/v1/records/${recordId}/provenance`),

  submitFeedback: (recordId: string, feedbackType: string, note?: string): Promise<unknown> =>
    request(`/api/v1/records/${recordId}/feedback`, {
      method: 'POST',
      body: JSON.stringify({ feedback_type: feedbackType, note }),
    }),

  // Datasets & Version Diff
  getDatasets: (): Promise<Dataset[]> =>
    request<Dataset[]>('/api/v1/datasets'),

  getDatasetVersions: (datasetId: string): Promise<DatasetVersion[]> =>
    request<DatasetVersion[]>(`/api/v1/datasets/${datasetId}/versions`),

  getDatasetDiff: (
    datasetId: string,
    fromVer: number,
    toVer: number
  ): Promise<{
    from_version: number;
    to_version: number;
    added: Array<{ key: string; data: Record<string, unknown> }>;
    removed: Array<{ key: string; data: Record<string, unknown> }>;
    changed: Array<{ key: string; field: string; old: unknown; new: unknown }>;
    schema_changed: boolean;
    summary: { added_count: number; removed_count: number; changed_count: number };
  }> =>
    request(`/api/v1/datasets/${datasetId}/diff?from_ver=${fromVer}&to_ver=${toVer}`),

  // Schedules
  getSchedules: (): Promise<Schedule[]> =>
    request<Schedule[]>('/api/v1/schedules'),

  createSchedule: (data: { workflow_id: string; cron_expression: string; label?: string }): Promise<Schedule> =>
    request<Schedule>('/api/v1/schedules', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateSchedule: (id: string, data: Partial<Schedule>): Promise<Schedule> =>
    request<Schedule>(`/api/v1/schedules/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  deleteSchedule: (id: string): Promise<{ deleted: string }> =>
    request<{ deleted: string }>(`/api/v1/schedules/${id}`, {
      method: 'DELETE',
    }),

  // History
  getHistory: (): Promise<HistoryItem[]> =>
    request<HistoryItem[]>('/api/v1/history'),

  // Utilities
  exportUrl: (runId: string, format: 'csv' | 'json' | 'xlsx' | 'report'): string =>
    `${BASE_URL}/api/v1/runs/${runId}/export?format=${format}`,

  streamUrl: (runId: string): string =>
    `${BASE_URL}/api/v1/runs/${runId}/stream`,
};
