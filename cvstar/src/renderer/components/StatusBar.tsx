import React from 'react';
import './StatusBar.css';

interface StatusBarProps {
  isCompiling: boolean;
  compilationError: string | null;
  onCompileLaTeX: () => void;
}

const StatusBar: React.FC<StatusBarProps> = ({ 
  isCompiling, 
  compilationError, 
  onCompileLaTeX 
}) => {
  return (
    <div className="status-bar">
      <div className="status-left">
        {isCompiling ? (
          <span className="status-compiling">Compiling...</span>
        ) : compilationError ? (
          <span className="status-error">Error: {compilationError}</span>
        ) : (
          <span className="status-ready">Ready</span>
        )}
      </div>
      <div className="status-right">
        <button 
          className="recompile-btn"
          onClick={onCompileLaTeX}
          disabled={isCompiling}
        >
          Recompile
        </button>
      </div>
    </div>
  );
};

export default StatusBar;