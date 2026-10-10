import React, { useState, useEffect, useRef } from 'react';
import MonacoEditor from '../components/MonacoEditor';
import PDFPreview from '../components/PDFPreview';
import StatusBar from '../components/StatusBar';
import './EditorPage.css';

interface EditorPageProps {
  projectId: number | null;
  onBackToProjects: () => void;
}

const EditorPage: React.FC<EditorPageProps> = ({ projectId, onBackToProjects }) => {
  const [latexContent, setLatexContent] = useState<string>( '');
  const [isCompiling, setIsCompiling] = useState<boolean>(false);
  const [compilationError, setCompilationError] = useState<string | null>(null);
  const [pdfData, setPdfData] = useState<string | null>(null);
  const [syncTexEnabled, setSyncTexEnabled] = useState<boolean>(true);
  const editorRef = useRef<any>(null);
  const projectDirRef = useRef<string>(''); // Would be set based on projectId in real app

  // Initialize sample LaTeX content for demo
  useEffect(() => {
    const sampleLatex = `% Sample LaTeX Resume
\\documentclass[11pt]{article}
\\usepackage[margin=1in]{geometry}
\\usepackage{enumitem}
\\setlist{itemsep=0pt}

\\begin{document}

\\begin{center}
    {\\LARGE \\bfseries John Doe}\\\\
    {\\large johndoe@email.com \\textbullet\ +1 (555) 123-4567 \\textbullet\ linkedin.com/in/johndoe}
\\end{center}

\\section*{Education}
\\begin{itemize}
    \\item Bachelor of Science in Computer Science, University of Example, 2020-2024
    \\item GPA: 3.8/4.0
\\end{itemize}

\\section*{Experience}
\\begin{itemize}
    \\item Software Engineering Intern, Tech Company, Summer 2023
    \\begin{itemize}[label=-]
        \\item Developed web applications using React and Node.js
        \\item Improved application performance by 20%
        \\item Collaborated with cross-functional team of 5 engineers
    \\end{itemize}
    \\item Research Assistant, University Lab, 2022-2023
    \\begin{itemize}[label=-]
        \\item Conducted research on machine learning algorithms
        \\item Published findings in undergraduate research journal
        \\item Presented results at campus research symposium
    \\end{itemize}
\\end{itemize}

\\section*{Skills}
\\begin{itemize}
    \\item Programming: JavaScript, Python, Java, C++
    \\item Web Technologies: React, Node.js, HTML/CSS, REST APIs
    \\item Tools: Git, Docker, VS Code, Linux
    \\item Languages: English (Native), Spanish (Intermediate)
\\end{itemize}

\\end{document}`;
    setLatexContent(sampleLatex);
    projectDirRef.current = '/tmp/cvstar-sample-project'; // In real app, this would be actual project directory
  }, []);

  const handleCompileLaTeX = async () => {
    setIsCompiling(true);
    setCompilationError(null);
    
    try {
      // Call Electron IPC to compile LaTeX
      const result = await (window as any).electronAPI.compileLaTeX(latexContent, projectDirRef.current);
      
      if (result.success) {
        setPdfData(result.pdfData);
        // In a real implementation, we would also handle SyncTeX here
      } else {
        setCompilationError(result.error || 'Compilation failed');
        console.error('Compilation error:', result.log);
      }
    } catch (error) {
      setCompilationError('Failed to compile LaTeX');
      console.error('LaTeX compilation error:', error);
    } finally {
      setIsCompiling(false);
    }
  };

  const handleContentChange = (newContent: string) => {
    setLatexContent(newContent);
  };

  return (
    <div className="editor-page">
      <div className="editor-header">
        <button className="back-btn" onClick={onBackToProjects}>
          ← Back to Projects
        </button>
        <div className="editor-title">
          Project {projectId} Editor
        </div>
        <div className="editor-controls">
          <button 
            className={`compile-btn ${isCompiling ? 'compiling' : ''}`}
            onClick={handleCompileLaTeX}
            disabled={isCompiling}
          >
            {isCompiling ? 'Compiling...' : 'Compile (Ctrl+S)'}
          </button>
          <button className="settings-btn">Settings</button>
          <button className="tools-btn">Tools ▼</button>
        </div>
      </div>
      
      <div className="editor-container">
        {/* Left panel: Editor */}
        <div className="editor-panel">
          <div className="editor-toolbar">
            <span className="file-name">main.tex</span>
            <div className="editor-tabs">
              <button className="tab active">Files</button>
              <button className="tab">Chats</button>
            </div>
          </div>
          <div className="editor-content">
            <MonacoEditor 
              value={latexContent}
              onChange={handleContentChange}
              ref={editorRef}
            />
          </div>
          {/* Outline section would go here in full implementation */}
          <div className="editor-outline">
            <h4>Outline</h4>
            <ul>
              <li>Education</li>
              <li>Experience</li>
              <li>Skills</li>
            </ul>
          </div>
        </div>
        
        {/* Right panel: PDF Preview */}
        <div className="preview-panel">
          <div className="preview-toolbar">
            <span className="page-info">Page 1 of 1</span>
            <div className="zoom-controls">
              <button className="zoom-out">−</button>
              <span className="zoom-level">100%</span>
              <button className="zoom-in">+</button>
            </div>
            <button className="preview-overflow">⋮</button>
          </div>
          <div className="preview-content">
            {pdfData ? (
              <PDFPreview 
                pdfData={pdfData} 
                syncTexEnabled={syncTexEnabled}
                onSyncTexChange={setSyncTexEnabled}
              />
            ) : (
              <div className="preview-placeholder">
                <p>Click "Compile" to generate PDF preview</p>
              </div>
            )}
          </div>
        </div>
      </div>
      
      {/* Bottom status/log panel */}
      <StatusBar 
        isCompiling={isCompiling}
        compilationError={compilationError}
        onCompileLaTeX={handleCompileLaTeX}
      />
    </div>
  );
};

export default EditorPage;