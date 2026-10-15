import React, { useState } from 'react';
import { ArrowRightLeft, X, ShieldAlert } from 'lucide-react';
import type { Item } from '../types';

interface TransferModalProps {
  item: Item;
  currentUser: string;
  onClose: () => void;
  onExecute: (id: number, targetUser: string, injectFault: boolean) => Promise<void>;
}

export const TransferModal: React.FC<TransferModalProps> = ({
  item,
  currentUser,
  onClose,
  onExecute,
}) => {
  const [targetUser, setTargetUser] = useState<string>(currentUser === 'alice' ? 'bob' : 'alice');
  const [injectFault, setInjectFault] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await onExecute(item.id, targetUser, injectFault);
      onClose();
    } catch {
      // handled
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <ArrowRightLeft size={18} className="text-indigo-400" />
            <h3 style={{ fontSize: '1.05rem', fontWeight: 600, color: '#fff' }}>
              Transfer Ownership Atomically
            </h3>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
          >
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: '0.78rem', color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
              Target Item:
            </label>
            <div style={{ fontSize: '0.88rem', fontWeight: 600, color: '#fff' }}>
              #{item.id}: {item.title}
            </div>
          </div>

          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: '0.78rem', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
              Transfer From:
            </label>
            <div className="owner-badge" style={{ padding: '4px 10px', fontSize: '0.85rem' }}>
              <strong>{item.owner}</strong> (Current Owner)
            </div>
          </div>

          <div style={{ marginBottom: 20 }}>
            <label style={{ fontSize: '0.78rem', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
              Transfer To:
            </label>
            <div style={{ display: 'flex', gap: 10 }}>
              {['alice', 'bob'].map((u) => (
                <button
                  key={u}
                  type="button"
                  className={`btn-secondary ${targetUser === u ? 'active' : ''}`}
                  style={{
                    flex: 1,
                    justifyContent: 'center',
                    borderColor: targetUser === u ? 'var(--accent-indigo)' : 'var(--border-subtle)',
                  }}
                  onClick={() => setTargetUser(u)}
                >
                  {u}
                </button>
              ))}
            </div>
          </div>

          <div
            style={{
              background: 'rgba(255, 255, 255, 0.02)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 8,
              padding: '12px',
              marginBottom: 20,
              cursor: 'pointer',
            }}
            onClick={() => setInjectFault(!injectFault)}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <ShieldAlert size={16} className={injectFault ? 'text-rose-400' : 'text-gray-400'} />
                <span style={{ fontSize: '0.82rem', color: injectFault ? '#fecdd3' : 'var(--text-secondary)' }}>
                  Inject Mid-Transaction Abort (Tests Rollback)
                </span>
              </div>
              <input type="checkbox" checked={injectFault} onChange={() => {}} />
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
            <button type="button" className="btn-secondary" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Processing...' : 'Execute Transaction'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
