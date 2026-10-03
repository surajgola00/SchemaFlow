// Field types
export type FieldType =
  | 'string'
  | 'number'
  | 'integer'
  | 'boolean'
  | 'date'
  | 'url'
  | 'email'
  | 'phone'
  | 'currency'
  | 'enum'
  | 'list';

export interface FieldSpec {
  name: string;
  label: string;
  type: FieldType;
  description: string;
  required: boolean;
  enum_values?: string[] | null;
  unique_key: boolean;
  validators: string[];
}

export interface SourceStrategy {
  connectors: string[];
  seed_queries: string[];
  seed_urls: string[];
  domain_allowlist: string[];
  domain_blocklist: string[];
  rationale: string;
}

export interface DagNode {
  id: string;
  type: string;
  depends_on: string[];
  params: Record<string, unknown>;
  label: string;
  status?: 'pending' | 'running' | 'succeeded' | 'failed' | 'skipped' | 'cancelled';
  items_in?: number;
  items_out?: number;
  error?: string | null;
}

export interface WorkflowSpec {
  title: string;
  intent_summary: string;
  entity_type: string;
  fields: FieldSpec[];
  source_strategy: SourceStrategy;
  dag: DagNode[];
  limits: Record<string, number>;
  assumptions: string[];
  clarifying_questions: string[];
  risk_notes: string[];
}

export interface Workflow {
  workflow_id: string;
  prompt: string;
  spec?: WorkflowSpec;
  target_schema: SchemaField[];
  execution_dag: DagStep[];
}

export interface SchemaField {
  name: string;
  type: string;
  required: boolean;
  description: string;
  unique_key?: boolean;
  validators?: string[];
}

export interface DagStep {
  step: number;
  name: string;
  description: string;
  id?: string;
  type?: string;
  depends_on?: string[];
  status?: 'pending' | 'running' | 'completed' | 'failed';
}

export interface ComplianceStatus {
  robots_txt_checked: boolean;
  rate_limited: boolean;
  permitted_domains: string[];
}

export interface NodeRun {
  id: string;
  run_id: string;
  node_id: string;
  status: 'pending' | 'running' | 'succeeded' | 'failed' | 'skipped' | 'cancelled';
  started_at?: string;
  finished_at?: string;
  items_in: number;
  items_out: number;
  error?: string | null;
}

export interface ExecutionRun {
  run_id: string;
  workflow_id: string;
  status: 'queued' | 'running' | 'paused' | 'completed' | 'partial' | 'failed' | 'cancelled';
  progress_pct: number;
  compliance_status: ComplianceStatus;
  logs: LogEntry[];
  created_at: string;
  finished_at?: string;
  engine_mode?: string;
  llm_mode?: string;
  metrics_json?: string;
}

export interface LogEntry {
  timestamp: string;
  level: 'INFO' | 'SUCCESS' | 'WARNING' | 'ERROR';
  message: string;
  node_id?: string;
}

export interface FieldProvenance {
  id: string;
  record_id: string;
  field_name: string;
  value: string | null;
  evidence_text: string;
  evidence_start: number;
  evidence_end: number;
  source_url: string;
  confidence: number;
  verified: boolean;
}

export interface ExtractedRecord {
  id: string;
  data: Record<string, unknown>;
  source_url: string;
  source_snippet: string;
  confidence_score: number;
  confidence?: number;
  is_duplicate: boolean;
  verification_status?: 'verified' | 'partial' | 'rejected';
  corroboration_count?: number;
  sources_json?: string;
  dedupe_key?: string;
  created_at?: string;
}

export interface SourceDocument {
  id: string;
  run_id: string;
  url: string;
  canonical_url: string;
  connector: string;
  status: 'fetched' | 'blocked' | 'failed';
  http_status: number;
  content_hash: string;
  fetched_at: string;
  blocked_reason?: string | null;
}

export interface QualityReport {
  run_id: string;
  rows_in: number;
  rows_out: number;
  duplicates_merged: number;
  verified_ratio: number;
  avg_confidence: number;
  validation_failures_by_reason: Record<string, number>;
  rejection_reasons_by_reason: Record<string, number>;
  fields_fixed_examples: Array<{ field: string; before: string; after: string }>;
}

export interface SSEEvent {
  type:
    | 'progress'
    | 'log'
    | 'record'
    | 'done'
    | 'node_started'
    | 'node_progress'
    | 'node_finished'
    | 'compliance'
    | 'metric'
    | 'run_state'
    | 'record_added';
  pct?: number;
  step?: string;
  level?: string;
  message?: string;
  count?: number;
  status?: string;
  node_id?: string;
  run_id?: string;
  ts?: string;
  timestamp?: string;
  data?: Record<string, unknown>;
}

export interface HistoryItem {
  workflow: {
    id: string;
    prompt: string;
    title?: string;
    entity_type?: string;
    target_schema?: SchemaField[];
    execution_dag?: DagStep[];
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

export interface Dataset {
  id: string;
  workflow_id: string;
  title: string;
  entity_type: string;
  created_at: string;
  updated_at: string;
  version_count: number;
  latest_version?: {
    version_no: number;
    record_count: number;
    created_at: string;
  } | null;
}

export interface DatasetVersion {
  id: string;
  dataset_id: string;
  version_no: number;
  run_id: string;
  created_at: string;
  record_count: number;
  quality_summary: Record<string, unknown>;
  schema_hash: string;
}

export interface Schedule {
  id: string;
  workflow_id: string;
  cron_expression: string;
  enabled: boolean;
  created_at: string;
  next_run_at?: string | null;
  last_run_id?: string | null;
  label: string;
}

export interface SystemStatus {
  llm_mode: 'live' | 'mock';
  model: string;
  search_provider: string;
  version: string;
}
