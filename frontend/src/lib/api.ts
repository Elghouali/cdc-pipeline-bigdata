import type {
  Alert,
  HealthItem,
  LoginRequest,
  MetricsResponse,
  Layer,
  QueryRow,
  Token,
  User,
} from '@/types/api';
import { parseNdjson } from './utils';

const BASE = '';

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem('cdc_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function checkOk(res: Response): Promise<void> {
  if (res.status === 401) {
    // Token expired or invalid — clear storage and redirect to login.
    localStorage.removeItem('cdc_token');
    localStorage.removeItem('cdc_user');
    window.location.assign('/');
    return;
  }
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // ignore parse error
    }
    throw new Error(detail);
  }
}

export async function fetchHealth(): Promise<HealthItem[]> {
  const res = await fetch(`${BASE}/api/health`, {
    headers: { ...authHeaders() },
  });
  await checkOk(res);
  return res.json() as Promise<HealthItem[]>;
}

export async function fetchMetrics(layer: Layer): Promise<MetricsResponse> {
  const res = await fetch(`${BASE}/api/metrics/${layer}`, {
    headers: { ...authHeaders() },
  });
  await checkOk(res);
  return res.json() as Promise<MetricsResponse>;
}

export async function runQuery(sql: string, signal?: AbortSignal): Promise<QueryRow[]> {
  const res = await fetch(`${BASE}/api/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ sql }),
    signal,
  });
  await checkOk(res);
  return parseNdjson<QueryRow>(res);
}

export async function login(body: LoginRequest): Promise<Token> {
  const res = await fetch(`${BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  await checkOk(res);
  return res.json() as Promise<Token>;
}

export async function fetchMe(): Promise<User> {
  const res = await fetch(`${BASE}/auth/me`, {
    headers: { ...authHeaders() },
  });
  await checkOk(res);
  return res.json() as Promise<User>;
}

export async function fetchAlerts(): Promise<Alert[]> {
  const res = await fetch(`${BASE}/api/alerts`, {
    headers: { ...authHeaders() },
  });
  await checkOk(res);
  return res.json() as Promise<Alert[]>;
}

export async function ackAlert(id: number, user: string): Promise<void> {
  const res = await fetch(`${BASE}/api/alerts/${id}/ack`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ user }),
  });
  await checkOk(res);
}
