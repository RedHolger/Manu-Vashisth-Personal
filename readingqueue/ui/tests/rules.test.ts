import { strict as assert } from 'node:assert';
import { describe, it } from 'node:test';
import { canEdit, listParams, getInsertSql, getListSql, getTransferSql } from '../src/rules.ts';

describe('reading-list rules (mirror backend)', () => {
  it('ownership gating', () => {
    assert.equal(canEdit('alice', 'alice'), true);
    assert.equal(canEdit('alice', 'bob'), false);
  });

  it('query builder caps paging like the backend', () => {
    assert.equal(listParams('Pump', 2, 500), 'search=Pump&page=2&per_page=50');
    assert.equal(listParams('', 0, 0), 'page=1&per_page=1');
  });

  it('generates valid PostgreSQL dialect queries', () => {
    const insertSql = getInsertSql('postgres', 'Clean Code', 'https://cleancode.org', 'alice');
    assert.ok(insertSql.includes('RETURNING id, owner, title, url, status'));

    const listSql = getListSql('postgres', 'Code', 1, 10);
    assert.ok(listSql.includes('LIMIT 10 OFFSET 0'));

    const transferSql = getTransferSql('postgres', 101, 'bob');
    assert.ok(transferSql.lock.includes('FOR UPDATE'));
  });

  it('generates valid SQL Server T-SQL dialect queries', () => {
    const insertSql = getInsertSql('sqlserver', 'Clean Code', 'https://cleancode.org', 'alice');
    assert.ok(insertSql.includes('OUTPUT INSERTED.id'));

    const listSql = getListSql('sqlserver', 'Code', 1, 10);
    assert.ok(listSql.includes('OFFSET 0 ROWS FETCH NEXT 10 ROWS ONLY'));

    const transferSql = getTransferSql('sqlserver', 101, 'bob');
    assert.ok(transferSql.lock.includes('WITH (UPDLOCK, ROWLOCK)'));
  });
});
