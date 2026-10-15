import React, { useState } from 'react';
import {
  Sparkles,
  X,
  CheckCircle,
  AlertCircle,
  ArrowRight,
  TrendingUp,
  FileCheck2,
  Layers,
} from 'lucide-react';
import type { AtsAnalysisResult, BulletRewrite } from '../../types';
import { JOB_TARGET_PRESETS } from '../../templates/sampleResumes';

interface AiTailorDrawerProps {
  onClose: () => void;
  analysis: AtsAnalysisResult;
  onApplyPatch: (rewrite: BulletRewrite) => void;
  onSelectPreset: (jobDesc: string) => void;
}

export const AiTailorDrawer: React.FC<AiTailorDrawerProps> = ({
  onClose,
  analysis,
  onApplyPatch,
  onSelectPreset,
}) => {
  const [selectedPreset, setSelectedPreset] = useState<string>('rakuten-kobo');
  const [appliedPatches, setAppliedPatches] = useState<Set<string>>(new Set());

  const handleApply = (rewrite: BulletRewrite) => {
    onApplyPatch(rewrite);
    setAppliedPatches((prev) => new Set(prev).add(rewrite.id));
  };

  const handlePresetChange = (presetId: string) => {
    setSelectedPreset(presetId);
    const preset = JOB_TARGET_PRESETS.find((p) => p.id === presetId);
    if (preset) {
      onSelectPreset(preset.description);
    }
  };

  return (
    <div className="ai-drawer">
      {/* Header */}
      <div className="ai-drawer-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Sparkles size={18} className="text-pink-400" />
          <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#fff' }}>
            AI Job Tailoring Engine
          </h3>
        </div>
        <button
          onClick={onClose}
          style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
        >
          <X size={18} />
        </button>
      </div>

      <div className="ai-drawer-content">
        {/* Target Job Presets */}
        <div style={{ marginBottom: 18 }}>
          <label style={{ fontSize: '0.78rem', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
            Target Job Profile:
          </label>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {JOB_TARGET_PRESETS.map((p) => (
              <button
                key={p.id}
                className={`btn-pill ${selectedPreset === p.id ? 'active' : ''}`}
                style={{
                  fontSize: '0.75rem',
                  borderColor: selectedPreset === p.id ? 'var(--accent-purple)' : 'var(--border-subtle)',
                  background: selectedPreset === p.id ? 'rgba(139, 92, 246, 0.15)' : 'var(--bg-tertiary)',
                  color: selectedPreset === p.id ? '#fff' : 'var(--text-secondary)',
                }}
                onClick={() => handlePresetChange(p.id)}
              >
                {p.company}
              </button>
            ))}
          </div>
        </div>

        {/* Moonshot Circular ATS Gauge */}
        <div className="ats-score-box" style={{ padding: '16px 12px 14px 12px' }}>
          <div className="score-gauge-container">
            <svg className="score-gauge-svg" viewBox="0 0 120 120">
              <defs>
                <linearGradient id="gauge-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#8b5cf6" />
                  <stop offset="50%" stopColor="#ec4899" />
                  <stop offset="100%" stopColor="#06b6d4" />
                </linearGradient>
              </defs>
              <circle cx="60" cy="60" r="48" className="gauge-track" />
              <circle
                cx="60"
                cy="60"
                r="48"
                className="gauge-fill"
                strokeDasharray="301.6"
                strokeDashoffset={301.6 - (analysis.matchScore / 100) * 301.6}
              />
            </svg>
            <div className="score-gauge-center">
              <div style={{ fontSize: '1.9rem', fontWeight: 800, color: '#fff', lineHeight: 1 }}>
                {analysis.matchScore}%
              </div>
              <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', marginTop: 3 }}>
                ATS Match
              </div>
            </div>
          </div>

          <div style={{ fontSize: '0.76rem', color: analysis.matchScore >= 80 ? '#34d399' : '#fbbf24', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4 }}>
            <TrendingUp size={13} />
            <span>{analysis.matchScore >= 80 ? 'Optimal Candidate Match' : 'Calibration Recommended'}</span>
          </div>
        </div>

        {/* Keyword Gaps Section */}
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: '0.82rem', fontWeight: 600, color: '#fff', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
            <Layers size={14} className="text-cyan-400" />
            <span>Keyword Gap Matrix</span>
          </div>

          {/* Matched Keywords */}
          <div style={{ marginBottom: 10 }}>
            <div style={{ fontSize: '0.72rem', color: '#34d399', marginBottom: 4, fontWeight: 600 }}>
              ✓ MATCHED SKILLS ({analysis.matchedKeywords.length}):
            </div>
            <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
              {analysis.matchedKeywords.map((k) => (
                <span
                  key={k}
                  style={{
                    fontSize: '0.72rem',
                    padding: '2px 7px',
                    borderRadius: 4,
                    background: 'rgba(16, 185, 129, 0.12)',
                    color: '#34d399',
                    border: '1px solid rgba(16, 185, 129, 0.25)',
                  }}
                >
                  {k}
                </span>
              ))}
            </div>
          </div>

          {/* Missing Keywords */}
          {analysis.missingKeywords.length > 0 && (
            <div>
              <div style={{ fontSize: '0.72rem', color: '#f43f5e', marginBottom: 4, fontWeight: 600 }}>
                ⚠ MISSING TARGET KEYWORDS ({analysis.missingKeywords.length}):
              </div>
              <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
                {analysis.missingKeywords.map((k) => (
                  <span
                    key={k}
                    style={{
                      fontSize: '0.72rem',
                      padding: '2px 7px',
                      borderRadius: 4,
                      background: 'rgba(244, 63, 94, 0.12)',
                      color: '#f43f5e',
                      border: '1px solid rgba(244, 63, 94, 0.25)',
                    }}
                  >
                    + {k}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Suggested Bullet Rewrites */}
        <div>
          <div style={{ fontSize: '0.82rem', fontWeight: 600, color: '#fff', marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
            <FileCheck2 size={14} className="text-indigo-400" />
            <span>Recommended Bullet Enhancements</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {analysis.bulletRewrites.map((rw) => {
              const isApplied = appliedPatches.has(rw.id);
              return (
                <div
                  key={rw.id}
                  style={{
                    background: 'var(--bg-tertiary)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 8,
                    padding: '12px 14px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{rw.section}</span>
                    <span style={{ fontSize: '0.7rem', color: '#34d399', background: 'rgba(16, 185, 129, 0.12)', padding: '1px 6px', borderRadius: 4, fontWeight: 600 }}>
                      {rw.metricGain}
                    </span>
                  </div>

                  <div style={{ fontSize: '0.76rem', color: '#9ca3af', marginBottom: 6, fontStyle: 'italic', borderLeft: '2px solid rgba(255,255,255,0.1)', paddingLeft: 8 }}>
                    "{rw.original.substring(0, 80)}..."
                  </div>

                  <div style={{ fontSize: '0.78rem', color: '#fff', marginBottom: 8, fontWeight: 500, borderLeft: '2px solid #8b5cf6', paddingLeft: 8 }}>
                    ↳ "{rw.rewritten}"
                  </div>

                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: 8 }}>
                    <strong>Rationale:</strong> {rw.rationale}
                  </div>

                  <button
                    className={`btn-pill ${isApplied ? 'btn-applied' : 'btn-ai-tailor'}`}
                    style={{ width: '100%', justifyContent: 'center', fontSize: '0.75rem', padding: '6px' }}
                    onClick={() => handleApply(rw)}
                    disabled={isApplied}
                  >
                    {isApplied ? (
                      <>
                        <CheckCircle size={13} color="#34d399" />
                        <span>Applied to LaTeX Source</span>
                      </>
                    ) : (
                      <>
                        <Sparkles size={13} />
                        <span>Apply Patch to Resume</span>
                      </>
                    )}
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
