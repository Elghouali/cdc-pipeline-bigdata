export type Role = 'admin' | 'viewer';
export type ServiceStatus = 'up' | 'down';
export type Layer = 'bronze' | 'silver' | 'gold';

export interface HealthItem {
  service: string;
  status: ServiceStatus;
  latency_ms: number | null;
  detail: string | null;
}

export interface TableMetric {
  table: string;
  row_count: number | null;
  latest_partition: string | null;
  error: string | null;
}

export interface MetricsResponse {
  layer: Layer;
  tables: TableMetric[];
  cached: boolean;
  generated_at: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface Token {
  access_token: string;
  token_type: string;
  expires_in: number;
  role: Role;
  username: string;
}

export interface User {
  id: number;
  username: string;
  role: Role;
  created_at: string | null;
}

export interface Alert {
  id: number;
  title: string;
  severity: string;
  fired_at: string;
  acknowledged_at: string | null;
  acknowledged_by: string | null;
}

export interface QueryRow {
  [key: string]: unknown;
}

export interface ApiError {
  detail: string;
}
