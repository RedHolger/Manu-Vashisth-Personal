import React from 'react';
import { X, CheckCircle, AlertTriangle, Info, FileCode } from 'lucide-react';
import type { LinterDiagnostic, AtsAnalysisResult } from '../../types';

interface LinterModalProps {
  onClose: () => void;
  diagnostics: LinterDiagnostic[];
  compliance: AtsAnalysisResult['complianceCheck'];
}

export const LinterModal: React.FC<LinterModalProps> = ({
  onClose,
  diagnostics,
  compliance,
}) => {
  return (
    <div className="modal-overlay" onClick={onClose} style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(0, 0, 0, 0.75)',
      backdropFilter: 'blur(4px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 100,
    }}>
      <div
        className="modal-content"
        onClick={(e) => e.stopPropagation()}
        style={{
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border-hover)',
          borderRadius: 12,
          width: '90%',
          maxWidth: 600,
          padding: 24,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <FileCode size={18} className="text-cyan-400" />
            <h3 style={{ fontSize: '1.05rem', fontWeight: 600, color: '#fff' }}>
              ChkTeX & ATS Compliance Diagnostics
            </h3>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
          >
            <X size={18} />
          </button>
        </div>

        {/* ATS Compliance Score */}
        <div
          style={{
            background: 'var(--bg-tertiary)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 8,
            padding: '14px 16px',
            marginBottom: 20,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div>
            <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#fff' }}>
              ATS Machine-Readability Index
            </div>
            <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
              Evaluates font glyph mapping, table column structure, and section headers
            </div>
          </div>
          <div style={{ fontSize: '1.3rem', fontWeight: 700, color: '#34d399' }}>
            {compliance.score}/100
          </div>
        </div>

        {/* Diagnostics list */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>
            Active Linter Rules & Findings:
          </div>

          {diagnostics.length === 0 ? (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '14px',
                borderRadius: 8,
                background: 'rgba(16, 185, 129, 0.08)',
                color: '#34d399',
                fontSize: '0.82rem',
              }}
            >
              <CheckCircle size={16} />
              <span>0 ChkTeX errors found. Document compiles with standard clean syntax.</span>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {diagnostics.map((d, idx) => (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: 10,
                    padding: '10px 12px',
                    borderRadius: 6,
                    background: 'var(--bg-tertiary)',
                    border: '1px solid var(--border-subtle)',
                    fontSize: '0.78rem',
                  }}
                >
                  {d.severity === 'warning' ? (
                    <AlertTriangle size={15} color="#fbbf24" style={{ marginTop: 2, flexShrink: 0 }} />
                  ) : (
                    <Info size={15} color="#38bdf8" style={{ marginTop: 2, flexShrink: 0 }} />
                  )}
                  <div style={{ flex: 1 }}>
                    <div style={{ color: '#fff', fontWeight: 500 }}>
                      Line {d.line}: <code>{d.code}</code>
                    </div>
                    <div style={{ color: 'var(--text-secondary)' }}>{d.message}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button className="btn-pill" onClick={onClose} style={{ padding: '6px 16px' }}>
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
};
