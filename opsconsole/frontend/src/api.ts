import type { Incident, Job, Role } from './types';

let role: Role = 'viewer';
let base = '';

export function setRole(r: Role): void {
  role = r;
}
export function getRole(): Role {
  return role;
}
// Test hook: point the client at a live backend (default '' = same origin).
export function setBase(url: string): void {
  base = url;
}

/** Stable key per logical action: an ambiguous-failure retry of the same
 * (action, job, version) reuses the key, so the server replays instead of
 * duplicating. A changed version is a new logical action -> new key. */
export function makeKey(action: 'retry' | 'cancel', id: number, version: number): string {
  return `ui-${action}-${id}-v${version}`;
}

/** Ambiguous outcome (request may or may not have mutated): network failure
 * or 5xx. Retrying with the SAME key is then safe. 4xx is decisive. */
export function isAmbiguous(err: unknown): boolean {
  if (err instanceof TypeError) return true; // fetch network failure
  const m = /(\d{3})/.exec(String(err));
  if (!m) return true; // unknown shape: assume ambiguous, key keeps it safe
  const code = parseInt(m[1], 10);
  return code >= 500;
}

async function req(path: string, init: RequestInit = {}): Promise<any> {
  const res = await fetch(base + path, {
    ...init,
    headers: { 'Content-Type': 'application/json', 'X-Role': role, ...(init.headers || {}) },
  });
  const body = await res.json();
  if (!res.ok) throw new Error(`${res.status}: ${body.error || 'request failed'}`);
  return body;
}

export const api = {
  jobs: (page = 1, status = '') =>
    req(`/api/jobs?page=${page}&per_page=5${status ? `&status=${status}` : ''}`),
  job: (id: number): Promise<Job> => req(`/api/jobs/${id}`),
  retry: (id: number, version: number, key: string) =>
    req(`/api/jobs/${id}/retry`, {
      method: 'POST',
      headers: { 'Idempotency-Key': key, 'If-Match': String(version) },
    }),
  cancel: (id: number, version: number, key: string) =>
    req(`/api/jobs/${id}/cancel`, {
      method: 'POST',
      headers: { 'Idempotency-Key': key, 'If-Match': String(version) },
    }),
  incidents: (): Promise<{ items: Incident[] }> => req('/api/incidents'),
};

/** One logical mutation with a single safe retry: the same stable key is
 * reused, so an ambiguous first attempt can only replay, never duplicate. */
export async function actWithRetry(
  kind: 'retry' | 'cancel', id: number, version: number,
): Promise<{ body: any; retried: boolean }> {
  const key = makeKey(kind, id, version);
  const once = () => kind === 'retry'
    ? api.retry(id, version, key)
    : api.cancel(id, version, key);
  try {
    return { body: await once(), retried: false };
  } catch (e) {
    if (!isAmbiguous(e)) throw e;
    return { body: await once(), retried: true };
  }
}
