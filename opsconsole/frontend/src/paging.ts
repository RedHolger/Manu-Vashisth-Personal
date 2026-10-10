// Pagination helpers shared by list views. Pure logic, unit-tested.
export function totalPages(total: number, perPage: number): number {
  if (perPage <= 0) throw new Error('perPage must be positive');
  return Math.max(1, Math.ceil(total / perPage));
}

export function clampPage(page: number, total: number, perPage: number): number {
  return Math.min(Math.max(1, page), totalPages(total, perPage));
}

export function pageSlice<T>(items: T[], page: number, perPage: number): T[] {
  const p = clampPage(page, items.length, perPage);
  return items.slice((p - 1) * perPage, p * perPage);
}
