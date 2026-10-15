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
  ArrowRight,
  GitCommit,
  Lock,
  Workflow,
  Sparkles,
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
      await new Promise((r) => setTimeout(r, 200));
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
    <div>
      {/* Top Banner: Kestra-inspired Workflow Pipeline Header */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
          <Workflow size={20} className="text-indigo-400" />
          <h2 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#fff' }}>
            ACID Transaction & Orchestration Topology
          </h2>
          <span className="brand-badge" style={{ background: 'rgba(6, 182, 212, 0.15)', color: '#38bdf8', borderColor: 'rgba(6, 182, 212, 0.3)' }}>
            Kestra Flow Model
          </span>
        </div>
        <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)' }}>
          Visualizes transactional state transitions, pessimistic concurrency locks, and mid-operation rollback guarantees across {currentDialect === 'postgres' ? 'PostgreSQL 16' : 'Microsoft SQL Server 2022'}.
        </p>
      </div>

      {/* Interactive Kestra-style DAG Flow Nodes */}
      <div className="kestra-dag-container">
        {/* Node 1 */}
        <div className={`dag-node ${result ? 'passed' : ''}`}>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 2 }}>
            Step 1
          </div>
          <div style={{ fontSize: '0.82rem', fontWeight: 600, color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
            <GitCommit size={14} color="#818cf8" />
            <span>BEGIN TRAN</span>
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 2 }}>
            Read Committed
          </div>
        </div>

        <div className="dag-arrow"><ArrowRight size={16} /></div>

        {/* Node 2 */}
        <div className={`dag-node ${result ? 'passed' : ''}`}>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 2 }}>
            Step 2
          </div>
          <div style={{ fontSize: '0.82rem', fontWeight: 600, color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
            <Lock size={14} color="#38bdf8" />
            <span>Row Lock</span>
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 2 }}>
            {currentDialect === 'postgres' ? 'FOR UPDATE' : 'UPDLOCK, ROWLOCK'}
          </div>
        </div>

        <div className="dag-arrow"><ArrowRight size={16} /></div>

        {/* Node 3 */}
        <div className={`dag-node ${result ? 'passed' : ''}`}>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 2 }}>
            Step 3
          </div>
          <div style={{ fontSize: '0.82rem', fontWeight: 600, color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
            <Layers size={14} color="#a78bfa" />
            <span>UPDATE Row</span>
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 2 }}>
            {currentDialect === 'postgres' ? 'RETURNING' : 'OUTPUT INSERTED'}
          </div>
        </div>

        <div className="dag-arrow"><ArrowRight size={16} /></div>

        {/* Node 4 (Hook) */}
        <div className={`dag-node ${result ? (injectFault ? 'failed' : 'passed') : ''}`}>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 2 }}>
            Step 4
          </div>
          <div style={{ fontSize: '0.82rem', fontWeight: 600, color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
            {injectFault ? <ShieldAlert size={14} color="#f43f5e" /> : <ShieldCheck size={14} color="#10b981" />}
            <span>Test Seam Hook</span>
          </div>
          <div style={{ fontSize: '0.7rem', color: injectFault ? '#f43f5e' : '#34d399', marginTop: 2 }}>
            {injectFault ? 'Fault Injected' : 'Hook Clean'}
          </div>
        </div>

        <div className="dag-arrow"><ArrowRight size={16} /></div>

        {/* Node 5 (Terminal Outcome) */}
        <div className={`dag-node ${result ? (result.rolledBack ? 'rollback' : 'passed') : ''}`}>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 2 }}>
            Final
          </div>
          <div style={{ fontSize: '0.82rem', fontWeight: 600, color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
            {result?.rolledBack ? <RotateCcw size={14} color="#fbbf24" /> : <CheckCircle size={14} color="#34d399" />}
            <span>{result ? (result.rolledBack ? 'ROLLBACK' : 'COMMIT') : 'COMMIT / ROLLBACK'}</span>
          </div>
          <div style={{ fontSize: '0.7rem', color: result?.rolledBack ? '#fbbf24' : '#34d399', marginTop: 2 }}>
            {result ? (result.rolledBack ? 'State Preserved' : 'Hardened to WAL') : 'Awaiting Run'}
          </div>
        </div>
      </div>

      {/* Main Controls & Log Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.3fr', gap: 24 }}>
        {/* Configuration Column */}
        <div className="linear-card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
            <ShieldCheck size={18} className="text-indigo-400" />
            <h3 style={{ fontSize: '0.98rem', fontWeight: 600, color: '#fff' }}>
              Transaction Parameters
            </h3>
          </div>

          {/* Selected Item */}
          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: '0.78rem', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
              Select Reading Item:
            </label>
            <select
              className="input-linear"
              style={{ width: '100%' }}
              value={selectedItemId}
              onChange={(e) => setSelectedItemId(Number(e.target.value))}
            >
              {items.map((it) => (
                <option key={it.id} value={it.id}>
                  #{it.id}: {it.title.substring(0, 46)}... (Owner: {it.owner})
                </option>
              ))}
            </select>
          </div>

          {/* Target Recipient */}
          <div style={{ marginBottom: 20 }}>
            <label style={{ fontSize: '0.78rem', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
              Target New Owner:
            </label>
            <div style={{ display: 'flex', gap: 8 }}>
              {['alice', 'bob'].map((u) => (
                <button
                  key={u}
                  type="button"
                  className={`btn-secondary ${targetUser === u ? 'active' : ''}`}
                  style={{
                    flex: 1,
                    justifyContent: 'center',
                    borderColor: targetUser === u ? 'var(--accent-indigo)' : 'var(--border-subtle)',
                    background: targetUser === u ? 'rgba(99, 102, 241, 0.12)' : 'var(--bg-tertiary)',
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
                  <div style={{ fontSize: '0.86rem', fontWeight: 600, color: injectFault ? '#fecdd3' : '#fff' }}>
                    Inject Mid-Transaction Abort
                  </div>
                  <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                    Triggers test seam failure hook to verify atomic ROLLBACK
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
              padding: '11px',
              background: injectFault
                ? 'linear-gradient(135deg, #e11d48 0%, #be123c 100%)'
                : 'linear-gradient(135deg, #4f46e5 0%, #06b6d4 100%)',
            }}
            onClick={handleRunTransaction}
            disabled={isExecuting}
          >
            {isExecuting ? (
              <>
                <Clock size={15} className="animate-spin" />
                <span>Orchestrating Transaction...</span>
              </>
            ) : (
              <>
                <Play size={15} />
                <span>
                  {injectFault ? 'Execute Faulted Transfer (Verify Rollback)' : 'Execute Atomic Transfer (Commit)'}
                </span>
              </>
            )}
          </button>
        </div>

        {/* Execution Trace & Proof Column */}
        <div className="linear-card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Terminal size={17} className="text-cyan-400" />
              <h3 style={{ fontSize: '0.96rem', fontWeight: 600, color: '#fff' }}>
                Engine Trace ({currentDialect === 'postgres' ? 'PostgreSQL 16' : 'SQL Server 2022'})
              </h3>
            </div>
            {result && (
              <span
                className={`status-pill ${result.rolledBack ? 'status-unread' : 'status-done'}`}
                style={{ fontSize: '0.72rem' }}
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
                fontSize: '0.84rem',
              }}
            >
              <Layers size={36} style={{ margin: '0 auto 12px auto', opacity: 0.3 }} />
              <p>Click "Execute" on the left to trigger real-time transaction orchestration.</p>
            </div>
          ) : (
            <div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 14 }}>
                {result.steps.map((st) => (
                  <div
                    key={st.id}
                    style={{
                      background: '#06070a',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 8,
                      padding: '10px 12px',
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        marginBottom: 4,
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        {st.status === 'success' ? (
                          <CheckCircle size={14} color="#34d399" />
                        ) : st.status === 'rolled_back' ? (
                          <RotateCcw size={14} color="#fbbf24" />
                        ) : (
                          <XCircle size={14} color="#f43f5e" />
                        )}
                        <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#fff' }}>
                          Step {st.step}: {st.description}
                        </span>
                      </div>
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                        {st.durationMs}ms
                      </span>
                    </div>

                    <div className="code-box" style={{ fontSize: '0.74rem', padding: '6px 8px', margin: '4px 0' }}>
                      {st.sql}
                    </div>

                    {st.detail && (
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                        ↳ {st.detail}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Verdict Proof Box */}
              <div
                style={{
                  background: result.rolledBack ? 'rgba(245, 158, 11, 0.08)' : 'rgba(16, 185, 129, 0.08)',
                  border: `1px solid ${result.rolledBack ? 'rgba(245, 158, 11, 0.3)' : 'rgba(16, 185, 129, 0.3)'}`,
                  borderRadius: 8,
                  padding: '10px 14px',
                  fontSize: '0.82rem',
                }}
              >
                <strong>Evaluation Evidence:</strong>{' '}
                {result.rolledBack
                  ? `Forced failure contained. Rollback verified: item #${selectedItemId} remained owned by '${result.item?.owner}'. Database consistency invariant holds.`
                  : `Transaction committed atomically. Row owner successfully updated to '${result.item?.owner}'.`}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
