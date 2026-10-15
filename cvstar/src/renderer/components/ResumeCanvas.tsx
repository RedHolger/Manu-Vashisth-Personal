import React, { useState } from 'react';
import { ZoomIn, ZoomOut, Maximize2, FileCheck } from 'lucide-react';

interface ResumeCanvasProps {
  latexSource: string;
}

export const ResumeCanvas: React.FC<ResumeCanvasProps> = ({ latexSource }) => {
  const [zoom, setZoom] = useState<number>(100);

  // Parse key sections from LaTeX
  const extractName = () => {
    const match = latexSource.match(/\\textbf\{\\Huge\s*\\scshape\s*([^}]+)\}/);
    return match ? match[1].trim() : 'Manu Vashisth';
  };

  const extractContact = () => {
    const match = latexSource.match(/\\small\s*([^\\end\{center\}]+?)\\\\end\{center\}/s) ||
                  latexSource.match(/\\small\s*([^\\]+)\\\\\s*\\vspace/s);
    if (!match) return 'Limerick, Ireland | +353 89 439 7650 | manuvashisth963@gmail.com | github.com/RedHolger';
    return match[1]
      .replace(/\\href\{[^}]+\}\{\\underline\{([^}]+)\}\}/g, '$1')
      .replace(/\\href\{[^}]+\}\{([^}]+)\}/g, '$1')
      .replace(/\\textbf\{[^}]+\}/g, '')
      .replace(/\\small/g, '')
      .replace(/\\vspace\{[^}]+\}/g, '')
      .replace(/\\\\/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  };

  const parseSections = () => {
    const sections: { title: string; content: string[] }[] = [];
    const sectionRegex = /\\section\{([^}]+)\}([\s\S]*?)(?=\\section\{|\\end\{document\})/g;
    let match;

    while ((match = sectionRegex.exec(latexSource)) !== null) {
      const title = match[1].trim();
      const rawContent = match[2].trim();

      // Extract items or subheadings
      const items: string[] = [];
      const itemRegex = /\\resumeItem\{([^}]+)\}/g;
      let itemMatch;
      while ((itemMatch = itemRegex.exec(rawContent)) !== null) {
        items.push(itemMatch[1].replace(/\\\\/g, '').replace(/\\%/g, '%').trim());
      }

      sections.push({ title, content: items });
    }

    return sections;
  };

  const name = extractName();
  const contact = extractContact();
  const sections = parseSections();

  return (
    <div className="preview-pane">
      {/* Top Preview Toolbar */}
      <div className="pane-toolbar">
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-muted)' }}>
          <FileCheck size={14} color="#34d399" />
          <span>Compiled Preview (Page 1 of 1)</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <button
            className="btn-pill"
            style={{ padding: '3px 8px' }}
            onClick={() => setZoom((z) => Math.max(70, z - 10))}
            title="Zoom Out"
          >
            <ZoomOut size={13} />
          </button>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', minWidth: 42, textAlign: 'center' }}>
            {zoom}%
          </span>
          <button
            className="btn-pill"
            style={{ padding: '3px 8px' }}
            onClick={() => setZoom((z) => Math.min(140, z + 10))}
            title="Zoom In"
          >
            <ZoomIn size={13} />
          </button>
          <button
            className="btn-pill"
            style={{ padding: '3px 8px' }}
            onClick={() => setZoom(100)}
            title="Reset Zoom"
          >
            <Maximize2 size={13} />
          </button>
        </div>
      </div>

      {/* A4 Sheet Area */}
      <div className="preview-scroll-area">
        <div
          className="resume-sheet"
          style={{ transform: `scale(${zoom / 100})`, transformOrigin: 'top center' }}
        >
          {/* Header */}
          <div className="resume-header">
            <h1 className="resume-name">{name}</h1>
            <div className="resume-contact">{contact}</div>
          </div>

          {/* Education Section */}
          <div className="resume-section-title">Education</div>
          <div className="resume-entry-header">
            <span>University of Limerick</span>
            <span>Limerick, Ireland</span>
          </div>
          <div className="resume-entry-sub">
            <span>Master of Science in Artificial Intelligence and Machine Learning</span>
            <span>2026 -- 2027</span>
          </div>

          <div className="resume-entry-header" style={{ marginTop: 4 }}>
            <span>Guru Gobind Singh Indraprastha University</span>
            <span>Delhi, India</span>
          </div>
          <div className="resume-entry-sub">
            <span>Bachelor of Technology in Computer Science (83.1%)</span>
            <span>2021 -- 2025</span>
          </div>

          {/* Technical Skills Section */}
          <div className="resume-section-title">Technical Skills</div>
          <div style={{ fontSize: '9.5pt', lineHeight: 1.45, marginBottom: 8 }}>
            <div><strong>Programming:</strong> Java 17+, Python, TypeScript, JavaScript, SQL, T-SQL, C++</div>
            <div><strong>Frameworks & Tools:</strong> Spring Boot, React, Vite, Node.js, Docker, Git, Electron, REST APIs</div>
            <div><strong>Database Systems:</strong> PostgreSQL 16, Microsoft SQL Server 2022, SQLite, Redis</div>
          </div>

          {/* Dynamic Experience & Projects */}
          {sections.map((sec, idx) => {
            if (sec.title.toLowerCase().includes('education') || sec.title.toLowerCase().includes('skills')) {
              return null;
            }
            return (
              <div key={idx}>
                <div className="resume-section-title">{sec.title}</div>
                {sec.content.length > 0 && (
                  <ul className="resume-bullets">
                    {sec.content.map((bullet, bIdx) => (
                      <li key={bIdx}>{bullet}</li>
                    ))}
                  </ul>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
