import type { DashboardResponse, TrendsResponse, BaselinePoint, WorkoutRecoveryResponse, AIInsight, PullStatusResponse, DataStatusResponse } from './types';

const BASE = '';  // Uses Next.js rewrites to proxy to FastAPI

export async function fetchDashboard(): Promise<DashboardResponse> {
  const res = await fetch(`${BASE}/api/dashboard`);
  if (!res.ok) throw new Error(`Dashboard fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchTrends(days = 30): Promise<TrendsResponse> {
  const res = await fetch(`${BASE}/api/trends?days=${days}`);
  if (!res.ok) throw new Error(`Trends fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchBaselines(metric: string): Promise<BaselinePoint[]> {
  const res = await fetch(`${BASE}/api/baselines?metric=${metric}`);
  if (!res.ok) throw new Error(`Baselines fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchWorkouts(days = 30): Promise<WorkoutRecoveryResponse> {
  const res = await fetch(`${BASE}/api/workouts?days=${days}`);
  if (!res.ok) throw new Error(`Workouts fetch failed: ${res.status}`);
  return res.json();
}

export async function refreshInsight(): Promise<AIInsight> {
  // Call backend directly to avoid Next.js proxy timeout (AI generation takes 10-20s)
  const res = await fetch(`http://localhost:8000/api/insights/refresh`, { method: 'POST' });
  if (res.status === 429) throw new Error('Rate limited. Try again in 60s.');
  if (!res.ok) throw new Error(`Insight refresh failed: ${res.status}`);
  return res.json();
}

export async function triggerPull(): Promise<PullStatusResponse> {
  const res = await fetch(`${BASE}/api/pipeline/pull`, { method: 'POST' });
  if (res.status === 409) throw new Error('Pull already in progress');
  if (!res.ok) throw new Error(`Pull trigger failed: ${res.status}`);
  return res.json();
}

export async function fetchPullStatus(): Promise<PullStatusResponse> {
  const res = await fetch(`${BASE}/api/pipeline/status`);
  if (!res.ok) throw new Error(`Pull status fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchDataStatus(): Promise<DataStatusResponse> {
  const res = await fetch(`${BASE}/api/data/status`);
  if (!res.ok) throw new Error(`Data status fetch failed: ${res.status}`);
  return res.json();
}
