export interface SchemaField {
  name: string;
  type: 'string' | 'number' | 'url' | 'email' | 'date';
  required: boolean;
  description: string;
}

export interface DagStep {
  step: number;
  name: string;
  description: string;
  status?: 'pending' | 'running' | 'completed' | 'failed';
}

export interface Workflow {
  workflow_id: string;
  prompt: string;
  target_schema: SchemaField[];
  execution_dag: DagStep[];
}

export interface ComplianceStatus {
  robots_txt_checked: boolean;
  rate_limited: boolean;
  permitted_domains: string[];
}

export interface ExecutionRun {
  run_id: string;
  workflow_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  progress_pct: number;
  compliance_status: ComplianceStatus;
  logs: LogEntry[];
  created_at: string;
  finished_at?: string;
}

export interface LogEntry {
  timestamp: string;
  level: 'INFO' | 'SUCCESS' | 'WARNING' | 'ERROR';
  message: string;
}

export interface ExtractedRecord {
  id: string;
  data: Record<string, any>;
  source_url: string;
  source_snippet: string;
  confidence_score: number;
  is_duplicate: boolean;
  created_at?: string;
}

export interface SSEEvent {
  type: 'progress' | 'log' | 'record' | 'done';
  pct?: number;
  step?: string;
  level?: string;
  message?: string;
  count?: number;
  status?: string;
}

export interface HistoryItem {
  workflow: {
    id: string;
    prompt: string;
    created_at: string;
  };
  runs: {
    run_id: string;
    status: string;
    record_count: number;
    created_at: string;
    finished_at?: string;
  }[];
}
