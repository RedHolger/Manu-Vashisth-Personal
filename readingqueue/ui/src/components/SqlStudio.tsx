import React, { useState } from 'react';
import { Database, Code2, Copy, Check } from 'lucide-react';

interface ComparisonFeature {
  id: string;
  title: string;
  description: string;
  postgres: string;
  sqlserver: string;
  keyDifference: string;
}

const COMPARISON_FEATURES: ComparisonFeature[] = [
  {
    id: 'pk',
    title: 'Table DDL & Primary Key Generation',
    description: 'Auto-incrementing surrogate keys and collation handling in V1__init.sql',
    postgres: `CREATE TABLE IF NOT EXISTS items (
    id BIGSERIAL PRIMARY KEY,
    owner VARCHAR(64) NOT NULL,
    title VARCHAR(512) NOT NULL,
    url VARCHAR(2048) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);`,
    sqlserver: `IF OBJECT_ID('items', 'U') IS NULL
CREATE TABLE items (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    owner NVARCHAR(64) NOT NULL,
    title NVARCHAR(512) NOT NULL,
    url NVARCHAR(2048) NOT NULL,
    created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);`,
    keyDifference: 'BIGSERIAL sequence in Postgres vs. BIGINT IDENTITY(1,1) in T-SQL. Unicode NVARCHAR and SYSUTCDATETIME() in SQL Server.',
  },
  {
    id: 'insert',
    title: 'Insert & Generated Key Retrieval',
    description: 'Atomic return of the newly allocated row after INSERT statement',
    postgres: `INSERT INTO items (owner, title, url, status)
VALUES (?, ?, ?, 'unread')
RETURNING id, owner, title, url, status;`,
    sqlserver: `INSERT INTO items (owner, title, url, status)
OUTPUT INSERTED.id, INSERTED.owner, INSERTED.title, INSERTED.url, INSERTED.status
VALUES (?, ?, ?, 'unread');`,
    keyDifference: 'Postgres uses RETURNING clause at the end of the query. SQL Server requires OUTPUT INSERTED.* placed between INSERT and VALUES.',
  },
  {
    id: 'paging',
    title: 'Deterministic Pagination',
    description: 'Ordering and slicing query results with per_page ceiling',
    postgres: `SELECT id, owner, title, url, status
FROM items
WHERE LOWER(title) LIKE LOWER(?)
ORDER BY id DESC
LIMIT ? OFFSET ?;`,
    sqlserver: `SELECT id, owner, title, url, status
FROM items
WHERE LOWER(title) LIKE LOWER(?)
ORDER BY id DESC
OFFSET ? ROWS FETCH NEXT ? ROWS ONLY;`,
    keyDifference: 'Postgres uses LIMIT / OFFSET. SQL Server 2022 uses standard ANSI OFFSET ... ROWS FETCH NEXT ... ROWS ONLY (requires ORDER BY).',
  },
  {
    id: 'lock',
    title: 'Concurrency & Pessimistic Row Locking',
    description: 'Preventing concurrent double-transfers or race conditions during ownership mutations',
    postgres: `SELECT id, owner FROM items 
WHERE id = ? 
FOR UPDATE;`,
    sqlserver: `SELECT id, owner FROM items 
WITH (UPDLOCK, ROWLOCK) 
WHERE id = ?;`,
    keyDifference: 'Postgres appends FOR UPDATE at the end of SELECT. T-SQL uses table lock hints WITH (UPDLOCK, ROWLOCK) directly after the table identifier.',
  },
];

export const SqlStudio: React.FC = () => {
  const [activeFeature, setActiveFeature] = useState<string>('pk');
  const [copiedSide, setCopiedSide] = useState<string | null>(null);

  const selected = COMPARISON_FEATURES.find((f) => f.id === activeFeature) || COMPARISON_FEATURES[0];

  const copyToClipboard = (text: string, side: string) => {
    navigator.clipboard.writeText(text);
    setCopiedSide(side);
    setTimeout(() => setCopiedSide(null), 1800);
  };

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#fff', marginBottom: 6 }}>
          Dual-Dialect SQL Architecture Studio
        </h2>
        <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)' }}>
          ReadingQueue enforces the exact same contract across PostgreSQL 16 and Microsoft SQL Server 2022.
          Below is a side-by-side inspection of how dialect-specific DDL and DML semantics are handled in the engine.
        </p>
      </div>

      {/* Feature Selector Pills */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
        {COMPARISON_FEATURES.map((f) => (
          <button
            key={f.id}
            className={`btn-secondary ${activeFeature === f.id ? 'active' : ''}`}
            style={{
              borderColor: activeFeature === f.id ? 'var(--accent-indigo)' : 'var(--border-subtle)',
              color: activeFeature === f.id ? '#fff' : 'var(--text-secondary)',
            }}
            onClick={() => setActiveFeature(f.id)}
          >
            <Code2 size={14} />
            <span>{f.title}</span>
          </button>
        ))}
      </div>

      {/* Comparison Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>
        {/* Postgres Column */}
        <div className="linear-card" style={{ borderTop: '3px solid #38bdf8' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Database size={16} color="#38bdf8" />
              <h3 style={{ fontSize: '0.92rem', fontWeight: 600, color: '#38bdf8' }}>
                PostgreSQL 16 Dialect
              </h3>
            </div>
            <button
              className="btn-secondary"
              style={{ padding: '4px 8px', fontSize: '0.74rem' }}
              onClick={() => copyToClipboard(selected.postgres, 'pg')}
            >
              {copiedSide === 'pg' ? <Check size={12} color="#34d399" /> : <Copy size={12} />}
              <span>{copiedSide === 'pg' ? 'Copied' : 'Copy SQL'}</span>
            </button>
          </div>

          <pre className="code-box" style={{ minHeight: 180, whiteSpace: 'pre-wrap' }}>
            {selected.postgres}
          </pre>
        </div>

        {/* SQL Server Column */}
        <div className="linear-card" style={{ borderTop: '3px solid #fb923c' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Database size={16} color="#fb923c" />
              <h3 style={{ fontSize: '0.92rem', fontWeight: 600, color: '#fb923c' }}>
                Microsoft SQL Server 2022 (T-SQL)
              </h3>
            </div>
            <button
              className="btn-secondary"
              style={{ padding: '4px 8px', fontSize: '0.74rem' }}
              onClick={() => copyToClipboard(selected.sqlserver, 'ms')}
            >
              {copiedSide === 'ms' ? <Check size={12} color="#34d399" /> : <Copy size={12} />}
              <span>{copiedSide === 'ms' ? 'Copied' : 'Copy T-SQL'}</span>
            </button>
          </div>

          <pre className="code-box" style={{ minHeight: 180, whiteSpace: 'pre-wrap' }}>
            {selected.sqlserver}
          </pre>
        </div>
      </div>

      {/* Difference Explanation Banner */}
      <div
        className="linear-card"
        style={{
          background: 'rgba(99, 102, 241, 0.06)',
          borderColor: 'rgba(99, 102, 241, 0.25)',
          padding: '16px 20px',
        }}
      >
        <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#c7d2fe', marginBottom: 4 }}>
          Dialect Engineering Analysis: {selected.title}
        </div>
        <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
          {selected.keyDifference}
        </p>
      </div>
    </div>
  );
};
