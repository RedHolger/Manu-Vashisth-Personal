export interface Rfi {
  id: string;
  title: string;
  owner: string;
  due: string;
  status: string;
  rev: number;
}

// Pure view helpers, unit-tested with node --test. `today` injected as
// YYYY-MM-DD so tests are deterministic (backend freezes 2026-10-08).
export function isOverdue(status: string, due: string, today: string): boolean {
  return status === 'open' && due < today;
}

export function dueLabel(status: string, due: string, today: string): string {
  if (status !== 'open') return status;
  if (due < today) return `OVERDUE since ${due}`;
  if (due === today) return 'due today';
  return `due ${due}`;
}

export function bucketByOwner(rfis: Rfi[]): Record<string, number> {
  const out: Record<string, number> = {};
  for (const r of rfis) {
    if (r.status === 'open') out[r.owner] = (out[r.owner] || 0) + 1;
  }
  return out;
}
