import type { Role } from './types';

// Mirrors the backend matrix. Pure logic, unit-tested with node --test.
export function can(role: Role, action: 'retry' | 'cancel' | 'act' | 'audit'): boolean {
  if (action === 'audit') return role === 'admin';
  if (role === 'viewer') return false;
  return role === 'operator' || role === 'admin';
}

export function retryAllowed(jobStatus: string): boolean {
  return jobStatus === 'failed';
}

export function cancelAllowed(jobStatus: string): boolean {
  return jobStatus === 'queued' || jobStatus === 'running';
}
