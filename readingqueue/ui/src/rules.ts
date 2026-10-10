export interface Item {
  id: number;
  owner: string;
  title: string;
  url: string;
  status: 'unread' | 'reading' | 'done';
}

// Ownership gating mirrors the backend 403. Pure logic, unit-tested.
export function canEdit(itemOwner: string, user: string): boolean {
  return itemOwner === user;
}

// Search/pagination query builder (backend caps per_page at 50).
export function listParams(search: string, page: number, perPage = 10): string {
  const p = new URLSearchParams();
  if (search) p.set('search', search);
  p.set('page', String(Math.max(1, page)));
  p.set('per_page', String(Math.min(50, Math.max(1, perPage))));
  return p.toString();
}
