export type Role = 'viewer' | 'operator' | 'admin';

export interface Job {
  id: number;
  name: string;
  status: 'queued' | 'running' | 'failed' | 'done' | 'canceled';
  version: number;
  runs: number[];
}

export interface Incident {
  id: number;
  title: string;
  severity: string;
  actions: string[];
}
