import React, { useState, useEffect, useMemo } from 'react';
import { Navbar } from './components/Navbar';
import { ResumeCanvas } from './components/ResumeCanvas';
import { AiTailorDrawer } from './components/AiTailorDrawer';
import { LinterModal } from './components/LinterModal';
import { TestModal } from './components/TestModal';
import { JAKE_TEMPLATE, JOB_TARGET_PRESETS } from '../templates/sampleResumes';
import { analyzeResume, applyBulletPatch, lintLatex } from '../services/aiTailoringEngine';
import type { BulletRewrite } from '../types';
import { Code2, Sparkles, Check, Copy } from 'lucide-react';
import './styles/theme.css';

const App: React.FC = () => {
  const [latexSource, setLatexSource] = useState<string>(JAKE_TEMPLATE);
  const [selectedTemplate, setSelectedTemplate] = useState<'jake' | 'modern' | 'research'>('jake');
  const [targetJobDesc, setTargetJobDesc] = useState<string>(JOB_TARGET_PRESETS[0].description);
  const [isCompiling, setIsCompiling] = useState<boolean>(false);
  const [isAiDrawerOpen, setIsAiDrawerOpen] = useState<boolean>(false);
  const [isLinterOpen, setIsLinterOpen] = useState<boolean>(false);
  const [isTestOpen, setIsTestOpen] = useState<boolean>(false);
  const [copiedCode, setCopiedCode] = useState<boolean>(false);

  // Compute ATS analysis whenever LaTeX source or Job Description changes
  const analysis = useMemo(() => {
    return analyzeResume(latexSource, targetJobDesc);
  }, [latexSource, targetJobDesc]);

  // Compute Linter diagnostics
  const diagnostics = useMemo(() => {
    return lintLatex(latexSource);
  }, [latexSource]);

  // Handle live edit
  const handleEditorChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setLatexSource(e.target.value);
    setIsCompiling(true);
    setTimeout(() => setIsCompiling(false), 200);
  };

  // Handle template switch
  const handleSelectTemplate = (tpl: 'jake' | 'modern' | 'research') => {
    setSelectedTemplate(tpl);
    setLatexSource(JAKE_TEMPLATE);
    setIsCompiling(true);
    setTimeout(() => setIsCompiling(false), 200);
  };

  // Apply surgical patch from AI Tailor
  const handleApplyPatch = (rewrite: BulletRewrite) => {
    const updated = applyBulletPatch(latexSource, rewrite);
    setLatexSource(updated);
    setIsCompiling(true);
    setTimeout(() => setIsCompiling(false), 200);
  };

  // Copy LaTeX code
  const handleCopyCode = () => {
    navigator.clipboard.writeText(latexSource);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 1500);
  };

  // Export / Print
  const handleExport = () => {
    window.print();
  };

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--bg-primary)' }}>
      {/* Top Navbar */}
      <Navbar
        onOpenAiTailor={() => setIsAiDrawerOpen(true)}
        onOpenLinter={() => setIsLinterOpen(true)}
        onOpenTests={() => setIsTestOpen(true)}
        onExport={handleExport}
        isCompiling={isCompiling}
        atsScore={analysis.matchScore}
        selectedTemplate={selectedTemplate}
        onSelectTemplate={handleSelectTemplate}
      />

      {/* Main Split-Screen Workspace */}
      <div className="workspace-container">
        {/* Left Side: LaTeX Code Editor */}
        <div className="editor-pane">
          <div className="pane-toolbar">
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#e2e8f0', fontWeight: 600 }}>
              <Code2 size={15} color="#818cf8" />
              <span>resume.tex</span>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 400 }}>
                ({latexSource.split('\n').length} lines)
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <button
                className="btn-pill"
                style={{ padding: '3px 8px', fontSize: '0.74rem' }}
                onClick={handleCopyCode}
              >
                {copiedCode ? <Check size={12} color="#34d399" /> : <Copy size={12} />}
                <span>{copiedCode ? 'Copied' : 'Copy'}</span>
              </button>

              <button
                className="btn-pill"
                style={{ padding: '3px 8px', fontSize: '0.74rem', background: 'rgba(99, 102, 241, 0.15)', color: '#818cf8' }}
                onClick={() => setIsAiDrawerOpen(true)}
              >
                <Sparkles size={12} />
                <span>AI Tailor</span>
              </button>
            </div>
          </div>

          <textarea
            className="editor-textarea"
            value={latexSource}
            onChange={handleEditorChange}
            spellCheck={false}
          />
        </div>

        {/* Right Side: Live Compiled Resume Canvas */}
        <ResumeCanvas latexSource={latexSource} />
      </div>

      {/* AI Tailoring Drawer */}
      {isAiDrawerOpen && (
        <AiTailorDrawer
          onClose={() => setIsAiDrawerOpen(false)}
          analysis={analysis}
          onApplyPatch={handleApplyPatch}
          onSelectPreset={(desc) => setTargetJobDesc(desc)}
        />
      )}

      {/* ChkTeX Linter Modal */}
      {isLinterOpen && (
        <LinterModal
          onClose={() => setIsLinterOpen(false)}
          diagnostics={diagnostics}
          compliance={analysis.complianceCheck}
        />
      )}

      {/* Automated Test Suite Modal */}
      {isTestOpen && <TestModal onClose={() => setIsTestOpen(false)} />}
    </div>
  );
};

export default App;