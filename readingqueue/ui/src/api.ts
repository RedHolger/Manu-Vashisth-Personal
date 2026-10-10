import type { Item } from './rules';
import { listParams } from './rules';

let user = 'alice';

export function setUser(u: string): void {
  user = u;
}
export function getUser(): string {
  return user;
}

async function req(path: string, init: RequestInit = {}): Promise<any> {
  const res = await fetch(path, {
    ...init,
    headers: { 'Content-Type': 'application/json', 'X-User': user, ...(init.headers || {}) },
  });
  const body = await res.json();
  if (!res.ok) throw new Error(`${res.status}: ${body.error || 'request failed'}`);
  return body;
}

export const api = {
  list: (search: string, page: number): Promise<{ items: Item[]; total: number }> =>
    req(`/api/items?${listParams(search, page)}`),
  add: (title: string, url: string): Promise<Item> =>
    req('/api/items', { method: 'POST', body: JSON.stringify({ title, url }) }),
  setStatus: (id: number, status: string): Promise<Item> =>
    req(`/api/items/${id}`, { method: 'PATCH', body: JSON.stringify({ status }) }),
  remove: (id: number): Promise<void> => {
    return req(`/api/items/${id}`, { method: 'DELETE' }).then(() => undefined);
  },
};
