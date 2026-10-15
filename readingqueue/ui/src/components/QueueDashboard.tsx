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
} from 'lucide-react';
import type { Item } from '../types';
import { canEdit } from '../rules';

interface QueueDashboardProps {
  items: Item[];
  currentUser: string;
  onUpdateStatus: (id: number, status: 'unread' | 'reading' | 'done') => void;
  onDelete: (id: number) => void;
  onStartTransfer: (item: Item) => void;
  onAddItem: (title: string, url: string, tags: string[]) => void;
  onSecurityAlert: (msg: string) => void;
}

export const QueueDashboard: React.FC<QueueDashboardProps> = ({
  items,
  currentUser,
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
