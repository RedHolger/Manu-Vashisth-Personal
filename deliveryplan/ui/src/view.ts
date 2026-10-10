export interface Task {
  title: string;
  team: string;
  owner: string;
  status: 'queued' | 'in-progress' | 'done' | 'blocked';
  start: string;
  dur: number;
  deps: string[];
}

// Pure view helpers, unit-tested with node --test.
export function driftLabel(days: number): string {
  if (days > 0) return `+${days}d late`;
  if (days < 0) return `${-days}d buffer`;
  return 'on track';
}

export function groupByStatus(ids: string[], tasks: Record<string, Task>): Record<string, string[]> {
  const groups: Record<string, string[]> = { queued: [], 'in-progress': [], done: [], blocked: [] };
  for (const id of ids) {
    const s = tasks[id].status;
    (groups[s] || (groups[s] = [])).push(id);
  }
  return groups;
}
