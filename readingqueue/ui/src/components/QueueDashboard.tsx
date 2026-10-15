import React, { useState } from 'react';
import {
  Search,
  Plus,
  BookOpen,
  CheckCircle2,
  ExternalLink,
  Trash2,
  ArrowRightLeft,
  Tag,
  AlertTriangle,
  Workflow,
  Database,
  ShieldCheck,
  ArrowRight,
} from 'lucide-react';
import type { Item, Dialect } from '../types';
import { canEdit } from '../rules';

interface QueueDashboardProps {
  items: Item[];
  currentUser: string;
  currentDialect: Dialect;
  onSelectTab: (tab: 'queue' | 'transactions' | 'sql' | 'tests') => void;
  onUpdateStatus: (id: number, status: 'unread' | 'reading' | 'done') => void;
  onDelete: (id: number) => void;
  onStartTransfer: (item: Item) => void;
  onAddItem: (title: string, url: string, tags: string[]) => void;
  onSecurityAlert: (msg: string) => void;
}

export const QueueDashboard: React.FC<QueueDashboardProps> = ({
  items,
  currentUser,
  currentDialect,
  onSelectTab,
  onUpdateStatus,
  onDelete,
  onStartTransfer,
  onAddItem,
  onSecurityAlert,
}) => {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [newTitle, setNewTitle] = useState('');
  const [newUrl, setNewUrl] = useState('');
  const [newTags, setNewTags] = useState('');

  const filteredItems = items.filter((item) => {
    const matchesSearch =
      item.title.toLowerCase().includes(search.toLowerCase()) ||
      (item.tags && item.tags.some((t) => t.toLowerCase().includes(search.toLowerCase())));
    const matchesStatus = statusFilter === 'all' || item.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const handleAddSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;
    const parsedTags = newTags
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);
    onAddItem(newTitle.trim(), newUrl.trim(), parsedTags);
    setNewTitle('');
    setNewUrl('');
    setNewTags('');
  };

  const handleUnauthorizedAction = (item: Item, actionName: string) => {
    onSecurityAlert(
      `403 Forbidden: Ownership Violation. '${currentUser}' cannot ${actionName} item #${item.id} because it is owned by '${item.owner}'. In accordance with the role model, users may only mutate their own items.`
    );
  };

  return (
    <div>
      {/* Kestra/Linear Enterprise Showcase Header */}
      <div
        className="linear-hero-card"
        style={{
          marginBottom: 24,
          padding: '22px 24px',
          background: 'linear-gradient(180deg, rgba(22, 26, 38, 0.75) 0%, rgba(13, 15, 21, 0.95) 100%)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          borderRadius: 12,
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16, flexWrap: 'wrap', gap: 12 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
              <span className="pulse-dot" />
              <h2 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#fff', letterSpacing: '-0.015em' }}>
                Enterprise Dual-Dialect Engine & ACID Concurrency Lab
              </h2>
              <span className="brand-badge" style={{ background: 'rgba(99, 102, 241, 0.18)', color: '#818cf8', borderColor: 'rgba(99, 102, 241, 0.35)' }}>
                Production Architecture
              </span>
            </div>
            <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)' }}>
              Dual PostgreSQL 16 & SQL Server 2022 migrations · Row-Level Security (403 gating) · Mid-transaction rollback hook
            </p>
          </div>

          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button
              type="button"
              onClick={() => onSelectTab('transactions')}
              className="btn-pill"
              style={{ background: 'rgba(99, 102, 241, 0.2)', borderColor: 'rgba(99, 102, 241, 0.4)', color: '#c7d2fe', fontWeight: 600 }}
              title="Inspect live ACID transaction topology graph (Press 2)"
            >
              <Workflow size={14} />
              <span>Kestra Workflow DAG</span>
              <kbd className="kbd-shortcut" style={{ background: 'rgba(0,0,0,0.3)', color: '#fff' }}>2</kbd>
            </button>
            <button
              type="button"
              onClick={() => onSelectTab('sql')}
              className="btn-pill"
              style={{ background: 'rgba(6, 182, 212, 0.15)', borderColor: 'rgba(6, 182, 212, 0.3)', color: '#38bdf8' }}
              title="Compare PostgreSQL 16 vs SQL Server queries (Press 3)"
            >
              <Database size={14} />
              <span>Dual SQL Studio</span>
              <kbd className="kbd-shortcut" style={{ background: 'rgba(0,0,0,0.3)', color: '#fff' }}>3</kbd>
            </button>
            <button
              type="button"
              onClick={() => onSelectTab('tests')}
              className="btn-pill"
              style={{ background: 'rgba(16, 185, 129, 0.15)', borderColor: 'rgba(16, 185, 129, 0.3)', color: '#34d399' }}
              title="Execute verified contract suite (Press 4)"
            >
              <ShieldCheck size={14} />
              <span>9/9 Tests Hub</span>
              <kbd className="kbd-shortcut" style={{ background: 'rgba(0,0,0,0.3)', color: '#fff' }}>4</kbd>
            </button>
          </div>
        </div>

        {/* Live Kestra Topology Preview Strip */}
        <div style={{ background: 'rgba(8, 9, 13, 0.75)', border: '1px solid var(--border-subtle)', borderRadius: 8, padding: '12px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: '0.8rem', color: 'var(--text-secondary)', flexWrap: 'wrap' }}>
            <span style={{ color: 'var(--text-muted)', textTransform: 'uppercase', fontSize: '0.68rem', letterSpacing: '0.05em' }}>
              Live ACID Topology:
            </span>
            <span style={{ color: '#818cf8', fontFamily: 'JetBrains Mono, monospace', fontSize: '0.78rem' }}>BEGIN TRAN</span>
            <ArrowRight size={13} color="#6b7280" />
            <span style={{ color: '#38bdf8', fontFamily: 'JetBrains Mono, monospace', fontSize: '0.78rem' }}>
              {currentDialect === 'postgres' ? 'FOR UPDATE' : 'UPDLOCK, ROWLOCK'}
            </span>
            <ArrowRight size={13} color="#6b7280" />
            <span style={{ color: '#a78bfa', fontFamily: 'JetBrains Mono, monospace', fontSize: '0.78rem' }}>
              {currentDialect === 'postgres' ? 'RETURNING id' : 'OUTPUT INSERTED.*'}
            </span>
            <ArrowRight size={13} color="#6b7280" />
            <span style={{ color: '#10b981', fontFamily: 'JetBrains Mono, monospace', fontSize: '0.78rem' }}>COMMIT / ROLLBACK</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 12, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            <span>Dialect: <strong style={{ color: '#fff' }}>{currentDialect === 'postgres' ? 'PostgreSQL 16' : 'SQL Server 2022'}</strong></span>
            <span>•</span>
            <span>Isolation: <strong style={{ color: '#34d399' }}>Read Committed</strong></span>
          </div>
        </div>
      </div>

      {/* Top Controls: Search & Filters */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: 260 }}>
          <Search
            size={16}
            style={{
              position: 'absolute',
              left: 14,
              top: '50%',
              transform: 'translateY(-50%)',
              color: 'var(--text-muted)',
            }}
          />
          <input
            type="text"
            className="input-linear"
            style={{ paddingLeft: 38, width: '100%' }}
            placeholder="Search items, titles, or tags..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div style={{ display: 'flex', gap: 6 }}>
          {['all', 'reading', 'unread', 'done'].map((st) => (
            <button
              key={st}
              className={`dialect-btn ${statusFilter === st ? 'active' : ''}`}
              style={{ textTransform: 'capitalize' }}
              onClick={() => setStatusFilter(st)}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Quick Add Bar */}
      <form onSubmit={handleAddSubmit} className="linear-card" style={{ marginBottom: 24, padding: 16 }}>
        <div style={{ fontSize: '0.82rem', fontWeight: 600, color: '#fff', marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
          <Plus size={14} className="text-indigo-400" />
          <span>Queue New Reading Item</span>
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <input
            type="text"
            className="input-linear"
            style={{ flex: 2, minWidth: 220 }}
            placeholder="Book or paper title..."
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
          />
          <input
            type="url"
            className="input-linear"
            style={{ flex: 1.5, minWidth: 180 }}
            placeholder="URL (optional)..."
            value={newUrl}
            onChange={(e) => setNewUrl(e.target.value)}
          />
          <input
            type="text"
            className="input-linear"
            style={{ flex: 1, minWidth: 140 }}
            placeholder="Tags (comma separated)..."
            value={newTags}
            onChange={(e) => setNewTags(e.target.value)}
          />
          <button type="submit" className="btn-primary" disabled={!newTitle.trim()}>
            <Plus size={14} />
            <span>Add</span>
          </button>
        </div>
      </form>

      {/* Items List */}
      <div className="items-grid">
        {filteredItems.length === 0 ? (
          <div
            className="linear-card"
            style={{
              textAlign: 'center',
              padding: '48px 20px',
              color: 'var(--text-muted)',
            }}
          >
            <BookOpen size={32} style={{ margin: '0 auto 12px auto', opacity: 0.4 }} />
            <p style={{ fontSize: '0.92rem' }}>No reading items match your search.</p>
          </div>
        ) : (
          filteredItems.map((item) => {
            const isOwner = canEdit(item.owner, currentUser);
            return (
              <div key={item.id} className="item-row">
                <div className="item-main">
                  <div className="item-header">
                    <span className={`status-pill status-${item.status}`}>{item.status}</span>
                    <a
                      href={item.url || '#'}
                      target={item.url ? '_blank' : '_self'}
                      rel="noreferrer"
                      className="item-title"
                    >
                      {item.title}
                    </a>
                    {item.url && (
                      <a href={item.url} target="_blank" rel="noreferrer" style={{ color: 'var(--text-muted)' }}>
                        <ExternalLink size={13} />
                      </a>
                    )}
                  </div>

                  <div className="item-meta">
                    <span className="owner-badge">
                      <span
                        className="avatar-dot"
                        style={{ background: item.owner === 'alice' ? '#38bdf8' : '#a78bfa' }}
                      ></span>
                      Owner: <strong>{item.owner}</strong> {isOwner ? '(You)' : ''}
                    </span>

                    {item.tags && item.tags.length > 0 && (
                      <span style={{ display: 'inline-flex', gap: 6 }}>
                        {item.tags.map((t, idx) => (
                          <span
                            key={idx}
                            style={{
                              fontSize: '0.72rem',
                              color: 'var(--text-secondary)',
                              background: 'rgba(255, 255, 255, 0.04)',
                              padding: '2px 6px',
                              borderRadius: 4,
                            }}
                          >
                            #{t}
                          </span>
                        ))}
                      </span>
                    )}

                    <span>ID #{item.id}</span>
                  </div>
                </div>

                <div className="item-actions">
                  {/* Status buttons */}
                  {item.status !== 'reading' && (
                    <button
                      className="btn-secondary"
                      onClick={() =>
                        isOwner
                          ? onUpdateStatus(item.id, 'reading')
                          : handleUnauthorizedAction(item, 'change status of')
                      }
                      title={isOwner ? 'Mark reading' : 'Requires ownership (403)'}
                    >
                      <BookOpen size={13} />
                      <span>Reading</span>
                    </button>
                  )}

                  {item.status !== 'done' && (
                    <button
                      className="btn-secondary"
                      onClick={() =>
                        isOwner
                          ? onUpdateStatus(item.id, 'done')
                          : handleUnauthorizedAction(item, 'mark done')
                      }
                      title={isOwner ? 'Mark done' : 'Requires ownership (403)'}
                    >
                      <CheckCircle2 size={13} />
                      <span>Done</span>
                    </button>
                  )}

                  {/* Transfer Ownership */}
                  <button
                    className="btn-secondary"
                    onClick={() =>
                      isOwner
                        ? onStartTransfer(item)
                        : handleUnauthorizedAction(item, 'transfer')
                    }
                    title={isOwner ? 'Transfer ownership atomically' : 'Requires ownership (403)'}
                  >
                    <ArrowRightLeft size={13} />
                    <span>Transfer</span>
                  </button>

                  {/* Delete button */}
                  <button
                    className="btn-danger"
                    onClick={() =>
                      isOwner
                        ? onDelete(item.id)
                        : handleUnauthorizedAction(item, 'delete')
                    }
                    title={isOwner ? 'Delete record' : 'Requires ownership (403)'}
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
