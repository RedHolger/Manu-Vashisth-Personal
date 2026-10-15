import type { Item, Dialect, TransactionResult, TransactionStep } from './types';
import { listParams, canEdit, getTransferSql } from './rules';
import { INITIAL_ITEMS } from './mockData';

let currentUser = 'alice';
let currentDialect: Dialect = 'postgres';
let memoryItems: Item[] = [...INITIAL_ITEMS];
let isLiveBackend = false;

// Check if backend is available
async function checkBackendConnection(): Promise<boolean> {
  try {
    const res = await fetch('/api/items?page=1&per_page=1', {
      headers: { 'X-User': currentUser },
      signal: AbortSignal.timeout(1200),
    });
    return res.ok;
  } catch {
    return false;
  }
}

// Initial check
checkBackendConnection().then((ok) => {
  isLiveBackend = ok;
});

export function setUser(u: string): void {
  currentUser = u;
}

export function getUser(): string {
  return currentUser;
}

export function setDialect(d: Dialect): void {
  currentDialect = d;
}

export function getDialect(): Dialect {
  return currentDialect;
}

export function getBackendStatus(): boolean {
  return isLiveBackend;
}

export const api = {
  checkHealth: async (): Promise<boolean> => {
    isLiveBackend = await checkBackendConnection();
    return isLiveBackend;
  },

  list: async (search: string, page: number, perPage = 10): Promise<{ items: Item[]; total: number; isMock: boolean }> => {
    if (isLiveBackend) {
      try {
        const res = await fetch(`/api/items?${listParams(search, page, perPage)}`, {
          headers: { 'X-User': currentUser },
        });
        if (res.ok) {
          const data = await res.json();
          return { items: data.items, total: data.total, isMock: false };
        }
      } catch {
        isLiveBackend = false;
      }
    }

    // In-memory filter / pagination
    let filtered = memoryItems;
    if (search.trim()) {
      const q = search.toLowerCase();
      filtered = memoryItems.filter((i) => i.title.toLowerCase().includes(q));
    }
    const total = filtered.length;
    const start = (Math.max(1, page) - 1) * perPage;
    const items = filtered.slice(start, start + perPage);
    return { items, total, isMock: true };
  },

  add: async (title: string, url: string, tags: string[] = []): Promise<{ item: Item; isMock: boolean }> => {
    if (!title.trim()) {
      throw new Error('400: Title cannot be empty');
    }

    if (isLiveBackend) {
      try {
        const res = await fetch('/api/items', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-User': currentUser },
          body: JSON.stringify({ title, url }),
        });
        if (res.ok) {
          const item = await res.json();
          return { item: { ...item, tags }, isMock: false };
        }
      } catch {
        isLiveBackend = false;
      }
    }

    const newItem: Item = {
      id: Math.max(...memoryItems.map((i) => i.id), 100) + 1,
      owner: currentUser,
      title: title.trim(),
      url: url.trim(),
      status: 'unread',
      createdAt: new Date().toISOString(),
      tags: tags.length ? tags : ['General'],
    };
    memoryItems = [newItem, ...memoryItems];
    return { item: newItem, isMock: true };
  },

  setStatus: async (id: number, status: 'unread' | 'reading' | 'done'): Promise<{ item: Item; isMock: boolean }> => {
    const existing = memoryItems.find((i) => i.id === id);
    if (existing && !canEdit(existing.owner, currentUser)) {
      throw new Error(`403: Ownership violation. Item #${id} is owned by '${existing.owner}'. '${currentUser}' cannot modify it.`);
    }

    if (isLiveBackend) {
      try {
        const res = await fetch(`/api/items/${id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json', 'X-User': currentUser },
          body: JSON.stringify({ status }),
        });
        if (res.ok) {
          const updated = await res.json();
          return { item: updated, isMock: false };
        }
        if (res.status === 403) {
          throw new Error(`403: Ownership violation. You do not own item #${id}.`);
        }
      } catch (err: any) {
        if (err.message.startsWith('403:')) throw err;
        isLiveBackend = false;
      }
    }

    if (!existing) {
      throw new Error(`404: Item #${id} not found`);
    }

    existing.status = status;
    memoryItems = memoryItems.map((i) => (i.id === id ? { ...existing } : i));
    return { item: { ...existing }, isMock: true };
  },

  remove: async (id: number): Promise<{ success: boolean; isMock: boolean }> => {
    const existing = memoryItems.find((i) => i.id === id);
    if (existing && !canEdit(existing.owner, currentUser)) {
      throw new Error(`403: Ownership violation. Item #${id} belongs to '${existing.owner}'. Only the owner can delete this record.`);
    }

    if (isLiveBackend) {
      try {
        const res = await fetch(`/api/items/${id}`, {
          method: 'DELETE',
          headers: { 'X-User': currentUser },
        });
        if (res.ok) {
          return { success: true, isMock: false };
        }
        if (res.status === 403) {
          throw new Error(`403: Ownership violation. You do not own item #${id}.`);
        }
      } catch (err: any) {
        if (err.message.startsWith('403:')) throw err;
        isLiveBackend = false;
      }
    }

    if (!existing) {
      throw new Error(`404: Item #${id} not found`);
    }

    memoryItems = memoryItems.filter((i) => i.id !== id);
    return { success: true, isMock: true };
  },

  // ACID Transaction simulator with Hook
  transfer: async (
    id: number,
    newOwner: string,
    injectFailure: boolean = false
  ): Promise<TransactionResult> => {
    const item = memoryItems.find((i) => i.id === id);
    if (!item) {
      throw new Error(`404: Item #${id} not found`);
    }

    if (!canEdit(item.owner, currentUser)) {
      throw new Error(`403: Forbidden. Only owner '${item.owner}' can initiate ownership transfer.`);
    }

    const sqlSnippets = getTransferSql(currentDialect, id, newOwner);
    const steps: TransactionStep[] = [];

    // Step 1: Begin Transaction
    steps.push({
      id: 'step-1',
      step: 1,
      description: 'Acquire database connection and start explicit transaction block',
      sql: sqlSnippets.begin,
      dialect: currentDialect,
      status: 'success',
      durationMs: 4,
      detail: currentDialect === 'postgres' ? 'READ COMMITTED snapshot established' : 'SQL Server explicit transaction started',
    });

    // Step 2: Row Lock
    steps.push({
      id: 'step-2',
      step: 2,
      description: `Select item record and lock target row to prevent concurrent mutations`,
      sql: sqlSnippets.lock,
      dialect: currentDialect,
      status: 'success',
      durationMs: 6,
      detail: currentDialect === 'postgres' ? 'FOR UPDATE row lock acquired' : 'UPDLOCK, ROWLOCK acquired on primary key',
    });

    // Step 3: Update Row
    steps.push({
      id: 'step-3',
      step: 3,
      description: `Update item owner from '${item.owner}' to '${newOwner}'`,
      sql: sqlSnippets.update,
      dialect: currentDialect,
      status: 'success',
      durationMs: 12,
      detail: currentDialect === 'postgres' ? 'RETURNING id, owner, title, url, status' : 'OUTPUT INSERTED.* captured in TDS packet',
    });

    // Step 4: Hook evaluation (Simulated mid-transaction exception)
    if (injectFailure) {
      steps.push({
        id: 'step-4',
        step: 4,
        description: 'Test Seam Hook: Injected forced mid-transaction failure (simulating network partition or unhandled exception)',
        sql: '-- EXCEPTION THROWN: java.lang.RuntimeException("Simulated network timeout before commit")',
        dialect: currentDialect,
        status: 'failed',
        durationMs: 2,
        detail: 'Simulated fault triggered during execution of post-update verification hook.',
      });

      // Rollback
      steps.push({
        id: 'step-5',
        step: 5,
        description: 'Transaction catch block invoked: rollback all uncommitted row modifications',
        sql: sqlSnippets.rollback,
        dialect: currentDialect,
        status: 'rolled_back',
        durationMs: 8,
        detail: `ROLLBACK complete. Item #${id} remains owned by original owner '${item.owner}'. Atomicity preserved.`,
      });

      return {
        success: false,
        item: { ...item },
        steps,
        rolledBack: true,
        error: 'Transaction aborted by injected failure test seam. Rollback verified: owner unchanged.',
      };
    }

    // Step 4 (Happy Path): Commit
    steps.push({
      id: 'step-4',
      step: 4,
      description: 'Transaction integrity confirmed: committing transaction to write-ahead log',
      sql: sqlSnippets.commit,
      dialect: currentDialect,
      status: 'success',
      durationMs: 9,
      detail: currentDialect === 'postgres' ? 'WAL flushed; row lock released' : 'SQL Server transaction log hardened; locks cleared',
    });

    // Apply state change
    const updatedItem = { ...item, owner: newOwner };
    memoryItems = memoryItems.map((i) => (i.id === id ? updatedItem : i));

    return {
      success: true,
      item: updatedItem,
      steps,
      rolledBack: false,
    };
  },

  resetData: (): void => {
    memoryItems = [...INITIAL_ITEMS];
  },
};
