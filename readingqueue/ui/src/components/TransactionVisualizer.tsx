import React, { useState } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  Play,
  RotateCcw,
  CheckCircle,
  XCircle,
  Clock,
  Layers,
  Terminal,
} from 'lucide-react';
import type { Item, Dialect, TransactionResult } from '../types';
import { api } from '../api';

interface TransactionVisualizerProps {
  items: Item[];
  currentUser: string;
  currentDialect: Dialect;
  onRefresh: () => void;
}

export const TransactionVisualizer: React.FC<TransactionVisualizerProps> = ({
  items,
  currentUser,
  currentDialect,
  onRefresh,
}) => {
  const eligibleItems = items.filter((i) => i.owner === currentUser);
  const [selectedItemId, setSelectedItemId] = useState<number>(
    eligibleItems.length ? eligibleItems[0].id : items[0]?.id || 101
  );
  const [targetUser, setTargetUser] = useState<string>(currentUser === 'alice' ? 'bob' : 'alice');
  const [injectFault, setInjectFault] = useState<boolean>(true);
  const [isExecuting, setIsExecuting] = useState<boolean>(false);
  const [result, setResult] = useState<TransactionResult | null>(null);

  const selectedItem = items.find((i) => i.id === selectedItemId);

  const handleRunTransaction = async () => {
    if (!selectedItem) return;
    setIsExecuting(true);
    setResult(null);

    try {
      // Simulate slight network delay for visual appreciation
      await new Promise((r) => setTimeout(r, 250));
      const res = await api.transfer(selectedItemId, targetUser, injectFault);
      setResult(res);
      onRefresh();
    } catch (err: any) {
      alert(`Transfer failed: ${err.message}`);
    } finally {
      setIsExecuting(false);
    }
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.3fr', gap: 24 }}>
      {/* Configuration Column */}
      <div className="linear-card">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
          <ShieldCheck size={20} className="text-indigo-400" />
          <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#fff' }}>
            ACID Transaction & Rollback Lab
          </h2>
        </div>

        <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', marginBottom: 20 }}>
          This visualizer executes the exact atomic transfer routine tested in{' '}
          <code className="font-mono text-purple-400">DbTest.testTransferRollbackOnHook</code>. When a
          mid-transaction error occurs, the transactional engine guarantees atomic rollback with zero
          state leakage.
        </p>

        {/* Selected Item */}
        <div style={{ marginBottom: 16 }}>
          <label style={{ fontSize: '0.78rem', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
            Select Target Item to Transfer:
          </label>
          <select
            className="input-linear"
            style={{ width: '100%' }}
            value={selectedItemId}
            onChange={(e) => setSelectedItemId(Number(e.target.value))}
          >
            {items.map((it) => (
              <option key={it.id} value={it.id}>
                #{it.id}: {it.title.substring(0, 48)}... (Owner: {it.owner})
              </option>
            ))}
          </select>
        </div>

        {/* Target Recipient */}
        <div style={{ marginBottom: 20 }}>
          <label style={{ fontSize: '0.78rem', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
            Transfer Ownership To:
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

        {/* Fault Injection Switch */}
        <div
          style={{
            background: injectFault ? 'rgba(244, 63, 94, 0.08)' : 'rgba(255, 255, 255, 0.02)',
            border: `1px solid ${injectFault ? 'rgba(244, 63, 94, 0.3)' : 'var(--border-subtle)'}`,
            borderRadius: 8,
            padding: '14px 16px',
            marginBottom: 24,
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
          onClick={() => setInjectFault(!injectFault)}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              {injectFault ? (
                <ShieldAlert size={18} className="text-rose-400" />
              ) : (
                <ShieldCheck size={18} className="text-emerald-400" />
              )}
              <div>
                <div style={{ fontSize: '0.88rem', fontWeight: 600, color: injectFault ? '#fecdd3' : '#fff' }}>
                  Inject Mid-Transaction Failure
                </div>
                <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
                  Simulates mid-transaction network abort to trigger atomic ROLLBACK
                </div>
              </div>
            </div>
            <input
              type="checkbox"
              checked={injectFault}
              onChange={() => {}}
              style={{ accentColor: 'var(--accent-rose)' }}
            />
          </div>
        </div>

        {/* Action Button */}
        <button
          className="btn-primary"
          style={{
            width: '100%',
            justifyContent: 'center',
            padding: '12px',
            background: injectFault
              ? 'linear-gradient(135deg, #e11d48 0%, #be123c 100%)'
              : 'linear-gradient(135deg, #4f46e5 0%, #06b6d4 100%)',
          }}
          onClick={handleRunTransaction}
          disabled={isExecuting}
        >
          {isExecuting ? (
            <>
              <Clock size={16} className="animate-spin" />
              <span>Executing Transaction...</span>
            </>
          ) : (
            <>
              <Play size={16} />
              <span>
                {injectFault ? 'Execute Faulted Transfer (Verify Rollback)' : 'Execute Clean Transfer (Commit)'}
              </span>
            </>
          )}
        </button>
      </div>

      {/* Execution Trace & Proof Column */}
      <div className="linear-card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Terminal size={18} className="text-cyan-400" />
            <h3 style={{ fontSize: '0.98rem', fontWeight: 600, color: '#fff' }}>
              Execution Trace ({currentDialect === 'postgres' ? 'PostgreSQL' : 'SQL Server'})
            </h3>
          </div>
          {result && (
            <span
              className={`status-pill ${result.rolledBack ? 'status-unread' : 'status-done'}`}
              style={{ fontSize: '0.75rem' }}
            >
              {result.rolledBack ? 'ROLLBACK VERIFIED' : 'COMMIT CONFIRMED'}
            </span>
          )}
        </div>

        {!result ? (
          <div
            style={{
              padding: '60px 20px',
              textAlign: 'center',
              color: 'var(--text-muted)',
              fontSize: '0.86rem',
            }}
          >
            <Layers size={36} style={{ margin: '0 auto 12px auto', opacity: 0.3 }} />
            <p>Click "Execute" on the left to observe live database transaction isolation.</p>
          </div>
        ) : (
          <div>
            {/* Step list */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 16 }}>
              {result.steps.map((st) => (
                <div
                  key={st.id}
                  style={{
                    background: '#07090e',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 8,
                    padding: '12px 14px',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      marginBottom: 6,
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      {st.status === 'success' ? (
                        <CheckCircle size={15} color="#34d399" />
                      ) : st.status === 'rolled_back' ? (
                        <RotateCcw size={15} color="#fbbf24" />
                      ) : (
                        <XCircle size={15} color="#f43f5e" />
                      )}
                      <span style={{ fontSize: '0.82rem', fontWeight: 600, color: '#fff' }}>
                        Step {st.step}: {st.description}
                      </span>
                    </div>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                      {st.durationMs}ms
                    </span>
                  </div>

                  <div className="code-box" style={{ fontSize: '0.76rem', padding: '8px 10px', margin: '4px 0' }}>
                    {st.sql}
                  </div>

                  {st.detail && (
                    <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', marginTop: 4 }}>
                      ↳ {st.detail}
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Verdict Box */}
            <div
              style={{
                background: result.rolledBack ? 'rgba(245, 158, 11, 0.08)' : 'rgba(16, 185, 129, 0.08)',
                border: `1px solid ${result.rolledBack ? 'rgba(245, 158, 11, 0.3)' : 'rgba(16, 185, 129, 0.3)'}`,
                borderRadius: 8,
                padding: '12px 16px',
                fontSize: '0.84rem',
              }}
            >
              <strong>Evaluation Proof:</strong>{' '}
              {result.rolledBack
                ? `Mid-transaction exception was safely contained. Row state was rolled back cleanly to owner '${result.item?.owner}'. Database consistency invariant holds.`
                : `Transaction committed atomically. Row owner successfully updated to '${result.item?.owner}'.`}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
