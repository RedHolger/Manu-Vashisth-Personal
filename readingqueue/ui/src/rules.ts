import type { Item, Dialect } from './types';

export type { Item, Dialect };

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

// Dialect SQL generator for UI introspection
export function getInsertSql(dialect: Dialect, title: string, url: string, owner: string): string {
  if (dialect === 'postgres') {
    return `INSERT INTO items (owner, title, url, status)
VALUES ('${owner}', '${title.replace(/'/g, "''")}', '${url.replace(/'/g, "''")}', 'unread')
RETURNING id, owner, title, url, status;`;
  } else {
    return `INSERT INTO items (owner, title, url, status)
OUTPUT INSERTED.id, INSERTED.owner, INSERTED.title, INSERTED.url, INSERTED.status
VALUES ('${owner}', N'${title.replace(/'/g, "''")}', N'${url.replace(/'/g, "''")}', 'unread');`;
  }
}

export function getListSql(dialect: Dialect, search: string, page: number, perPage: number): string {
  const offset = (Math.max(1, page) - 1) * perPage;
  const where = search ? `WHERE LOWER(title) LIKE LOWER('%${search.replace(/'/g, "''")}%')` : '';
  
  if (dialect === 'postgres') {
    return `SELECT id, owner, title, url, status
FROM items
${where}
ORDER BY id DESC
LIMIT ${perPage} OFFSET ${offset};`;
  } else {
    return `SELECT id, owner, title, url, status
FROM items
${where}
ORDER BY id DESC
OFFSET ${offset} ROWS FETCH NEXT ${perPage} ROWS ONLY;`;
  }
}

export function getTransferSql(dialect: Dialect, id: number, newOwner: string): { begin: string; lock: string; update: string; commit: string; rollback: string } {
  if (dialect === 'postgres') {
    return {
      begin: 'BEGIN TRANSACTION ISOLATION LEVEL READ COMMITTED;',
      lock: `SELECT id, owner FROM items WHERE id = ${id} FOR UPDATE;`,
      update: `UPDATE items SET owner = '${newOwner}' WHERE id = ${id} RETURNING id, owner, title, url, status;`,
      commit: 'COMMIT;',
      rollback: 'ROLLBACK;',
    };
  } else {
    return {
      begin: 'SET TRANSACTION ISOLATION LEVEL READ COMMITTED;\nBEGIN TRANSACTION;',
      lock: `SELECT id, owner FROM items WITH (UPDLOCK, ROWLOCK) WHERE id = ${id};`,
      update: `UPDATE items SET owner = '${newOwner}' OUTPUT INSERTED.id, INSERTED.owner, INSERTED.title, INSERTED.url, INSERTED.status WHERE id = ${id};`,
      commit: 'COMMIT TRANSACTION;',
      rollback: 'ROLLBACK TRANSACTION;',
    };
  }
}
