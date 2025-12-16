import type {
  ClusterStatus,
  WorkerInfo,
  AppInfo,
  JobSubmitRequest,
  JobSubmitResponse,
} from '../types/types';

const API_BASE = 'http://localhost:8000/api/v1';

export async function getClusterStatus(): Promise<ClusterStatus> {
  const response = await fetch(`${API_BASE}/cluster/status`);
  if (!response.ok) {
    throw new Error('Failed to fetch cluster status');
  }
  return response.json();
}

export async function getWorkers(): Promise<WorkerInfo[]> {
  const response = await fetch(`${API_BASE}/cluster/workers`);
  if (!response.ok) {
    throw new Error('Failed to fetch workers');
  }
  return response.json();
}

export async function getApps(includeCompleted: boolean = false): Promise<AppInfo[]> {
  const response = await fetch(
    `${API_BASE}/jobs/apps?include_completed=${includeCompleted}`
  );
  if (!response.ok) {
    throw new Error('Failed to fetch apps');
  }
  return response.json();
}

export async function submitJob(request: JobSubmitRequest): Promise<JobSubmitResponse> {
  const response = await fetch(`${API_BASE}/jobs/submit`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to submit job');
  }
  return response.json();
}

export async function killJob(appId: string): Promise<JobSubmitResponse> {
  const response = await fetch(`${API_BASE}/jobs/apps/${appId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to kill job');
  }
  return response.json();
}