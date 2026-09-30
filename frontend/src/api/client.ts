const BASE_URL = 'http://localhost:8000';

export const api = {
  compile: (prompt: string, useMock: boolean) =>
    fetch(`${BASE_URL}/api/v1/compile`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, use_mock: useMock })
    }).then(r => r.json()),

  startRun: (data: { workflow_id: string; approved_schema: any[]; approved_dag: any[]; use_mock: boolean }) =>
    fetch(`${BASE_URL}/api/v1/runs/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }).then(r => r.json()),

  getRun: (runId: string) =>
    fetch(`${BASE_URL}/api/v1/runs/${runId}`).then(r => r.json()),

  getRecords: (runId: string, page = 1, search = '') =>
    fetch(`${BASE_URL}/api/v1/runs/${runId}/records?page=${page}&search=${encodeURIComponent(search)}`).then(r => r.json()),

  getHistory: () =>
    fetch(`${BASE_URL}/api/v1/history`).then(r => r.json()),

  exportUrl: (runId: string, format: 'csv' | 'json') =>
    `${BASE_URL}/api/v1/runs/${runId}/export?format=${format}`,

  streamUrl: (runId: string) =>
    `${BASE_URL}/api/v1/runs/${runId}/stream`,
};
