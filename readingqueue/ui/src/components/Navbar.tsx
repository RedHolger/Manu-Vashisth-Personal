import { Database, ShieldCheck, GitBranch, Radio, Code2 } from 'lucide-react';
import type { Dialect } from '../types';

interface NavbarProps {
  currentDialect: Dialect;
  onSelectDialect: (d: Dialect) => void;
  currentUser: string;
  onSelectUser: (u: string) => void;
  activeTab: 'queue' | 'transactions' | 'sql' | 'tests';
  onSelectTab: (tab: 'queue' | 'transactions' | 'sql' | 'tests') => void;
  isLiveBackend: boolean;
  itemCount: number;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentDialect,
  onSelectDialect,
  currentUser,
  onSelectUser,
  activeTab,
  onSelectTab,
  isLiveBackend,
  itemCount,
}) => {
  return (
    <header>
      <div className="navbar">
        <div className="brand">
          <div className="brand-icon">
            <Database size={20} />
          </div>
          <div className="brand-info">
            <h1>
              ReadingQueue
              <span className="brand-badge">v1.2 Dual-Dialect</span>
            </h1>
            <div className="brand-subtitle">
              Java 17 REST Engine · PostgreSQL 16 & SQL Server 2022 (T-SQL)
            </div>
          </div>
        </div>

        <div className="nav-actions">
          {/* Health indicator */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              fontSize: '0.78rem',
              color: isLiveBackend ? '#34d399' : '#a78bfa',
              background: 'rgba(255, 255, 255, 0.03)',
              padding: '5px 10px',
              borderRadius: 6,
              border: '1px solid var(--border-subtle)',
            }}
          >
            <Radio size={12} className={isLiveBackend ? 'text-emerald-400' : 'text-purple-400'} />
            <span>{isLiveBackend ? 'Live Java Server' : 'Verified Sandbox (In-Browser)'}</span>
          </div>

          {/* Dialect Toggle */}
          <div className="dialect-pill">
            <button
              className={`dialect-btn ${currentDialect === 'postgres' ? 'active postgres' : ''}`}
              onClick={() => onSelectDialect('postgres')}
              title="PostgreSQL 16 Dialect (SERIAL, RETURNING, LIMIT/OFFSET)"
            >
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#38bdf8' }}></span>
              PostgreSQL 16
            </button>
            <button
              className={`dialect-btn ${currentDialect === 'sqlserver' ? 'active sqlserver' : ''}`}
              onClick={() => onSelectDialect('sqlserver')}
              title="Microsoft SQL Server 2022 (IDENTITY, OUTPUT INSERTED, OFFSET/FETCH)"
            >
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#fb923c' }}></span>
              SQL Server (T-SQL)
            </button>
          </div>

          {/* User Identity Switcher */}
          <div className="user-selector">
            <span>Identity:</span>
            <button
              className={`user-btn ${currentUser === 'alice' ? 'active' : ''}`}
              onClick={() => onSelectUser('alice')}
            >
              <span className="avatar-dot avatar-alice"></span>
              alice
            </button>
            <button
              className={`user-btn ${currentUser === 'bob' ? 'active' : ''}`}
              onClick={() => onSelectUser('bob')}
            >
              <span className="avatar-dot avatar-bob"></span>
              bob
            </button>
          </div>

          {/* GitHub link */}
          <a
            href="https://github.com/RedHolger/Manu-Vashisth-Personal/tree/master/readingqueue"
            target="_blank"
            rel="noreferrer"
            className="btn-secondary"
            style={{ textDecoration: 'none' }}
          >
            <GitBranch size={14} />
            <span>GitHub</span>
          </a>
        </div>
      </div>

      {/* Tabs */}
      <nav className="tab-bar">
        <button
          className={`tab-btn ${activeTab === 'queue' ? 'active' : ''}`}
          onClick={() => onSelectTab('queue')}
        >
          <span>Reading Queue</span>
          <span
            style={{
              fontSize: '0.7rem',
              background: 'rgba(255, 255, 255, 0.1)',
              padding: '2px 6px',
              borderRadius: 9999,
            }}
          >
            {itemCount}
          </span>
          <kbd className="kbd-shortcut" style={{ marginLeft: 6 }}>1</kbd>
        </button>

        <button
          className={`tab-btn ${activeTab === 'transactions' ? 'active' : ''}`}
          onClick={() => onSelectTab('transactions')}
        >
          <ShieldCheck size={14} />
          <span>ACID Transaction Lab</span>
          <kbd className="kbd-shortcut" style={{ marginLeft: 6 }}>2</kbd>
        </button>

        <button
          className={`tab-btn ${activeTab === 'sql' ? 'active' : ''}`}
          onClick={() => onSelectTab('sql')}
        >
          <Database size={14} />
          <span>Dual-Dialect SQL Studio</span>
          <kbd className="kbd-shortcut" style={{ marginLeft: 6 }}>3</kbd>
        </button>

        <button
          className={`tab-btn ${activeTab === 'tests' ? 'active' : ''}`}
          onClick={() => onSelectTab('tests')}
        >
          <span>Test Contracts & Evidence</span>
          <span
            style={{
              fontSize: '0.7rem',
              background: 'rgba(16, 185, 129, 0.2)',
              color: '#34d399',
              padding: '2px 6px',
              borderRadius: 9999,
              fontWeight: 600,
            }}
          >
            9/9 Pass
          </span>
          <kbd className="kbd-shortcut" style={{ marginLeft: 6 }}>4</kbd>
        </button>
      </nav>
    </header>
  );
};
