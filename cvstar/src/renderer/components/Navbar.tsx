import React from 'react';
import {
  Sparkles,
  FileCode,
  ShieldCheck,
  Download,
  GitBranch,
  CheckCircle,
  FileText,
} from 'lucide-react';

interface NavbarProps {
  onOpenAiTailor: () => void;
  onOpenLinter: () => void;
  onOpenTests: () => void;
  onExport: () => void;
  isCompiling: boolean;
  atsScore: number;
  selectedTemplate: string;
  onSelectTemplate: (tpl: 'jake' | 'modern' | 'research') => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  onOpenAiTailor,
  onOpenLinter,
  onOpenTests,
  onExport,
  isCompiling,
  atsScore,
  selectedTemplate,
  onSelectTemplate,
}) => {
  return (
    <header className="cvstar-header">
      <div className="cvstar-brand">
        <div className="brand-gem">
          <Sparkles size={16} />
        </div>
        <div className="brand-title">
          <span>CVStar</span>
          <span
            style={{
              fontSize: '0.65rem',
              fontWeight: 600,
              padding: '2px 6px',
              borderRadius: 4,
              background: 'rgba(99, 102, 241, 0.15)',
              color: '#818cf8',
              border: '1px solid rgba(99, 102, 241, 0.3)',
            }}
          >
            ATS LaTeX Workspace
          </span>
        </div>
      </div>

      {/* Middle: Template selector & compilation badge */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          <FileText size={14} />
          <span>Template:</span>
          <select
            value={selectedTemplate}
            onChange={(e) => onSelectTemplate(e.target.value as any)}
            style={{
              background: 'var(--bg-tertiary)',
              color: '#fff',
              border: '1px solid var(--border-subtle)',
              borderRadius: 6,
              padding: '4px 8px',
              fontSize: '0.78rem',
              cursor: 'pointer',
              outline: 'none',
            }}
          >
            <option value="jake">Jake's Resume (ATS Standard)</option>
            <option value="modern">Modern SWE (High Density)</option>
            <option value="research">AI/ML Research Curriculum</option>
          </select>
        </div>

        <div
          style={{
            fontSize: '0.75rem',
            padding: '4px 10px',
            borderRadius: 6,
            background: isCompiling ? 'rgba(245, 158, 11, 0.15)' : 'rgba(16, 185, 129, 0.12)',
            color: isCompiling ? '#fbbf24' : '#34d399',
            border: `1px solid ${isCompiling ? 'rgba(245, 158, 11, 0.3)' : 'rgba(16, 185, 129, 0.25)'}`,
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}
        >
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: isCompiling ? '#fbbf24' : '#34d399',
            }}
          />
          <span>{isCompiling ? 'Compiling LaTeX...' : 'Real-time Preview Ready'}</span>
        </div>
      </div>

      {/* Right Actions */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        {/* ATS Score Indicator */}
        <button
          className="btn-pill"
          onClick={onOpenAiTailor}
          style={{
            background: 'rgba(99, 102, 241, 0.12)',
            borderColor: 'rgba(99, 102, 241, 0.3)',
            color: '#c7d2fe',
          }}
        >
          <Sparkles size={14} className="text-pink-400" />
          <span>ATS Score: <strong>{atsScore}%</strong></span>
        </button>

        {/* AI Tailor Primary Action */}
        <button className="btn-pill btn-ai-tailor" onClick={onOpenAiTailor}>
          <Sparkles size={14} />
          <span>Tailor to Job</span>
        </button>

        {/* ChkTeX Linter */}
        <button className="btn-pill" onClick={onOpenLinter} title="ChkTeX & ATS Format Linter">
          <FileCode size={14} />
          <span>Linter</span>
        </button>

        {/* Tests */}
        <button className="btn-pill" onClick={onOpenTests} title="Automated Verification Suite">
          <ShieldCheck size={14} color="#34d399" />
          <span>5/5 Tests</span>
        </button>

        {/* Download PDF */}
        <button className="btn-pill" onClick={onExport} title="Export clean formatted resume">
          <Download size={14} />
          <span>Export</span>
        </button>

        {/* GitHub link */}
        <a
          href="https://github.com/RedHolger/Manu-Vashisth-Personal/tree/master/cvstar"
          target="_blank"
          rel="noreferrer"
          className="btn-pill"
          style={{ textDecoration: 'none' }}
        >
          <GitBranch size={14} />
          <span>GitHub</span>
        </a>
      </div>
    </header>
  );
};
