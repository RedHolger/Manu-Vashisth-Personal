import { strict as assert } from 'node:assert';
import { describe, it } from 'node:test';
import { canEdit, listParams } from '../src/rules.ts';

describe('reading-list rules (mirror backend)', () => {
  it('ownership gating', () => {
    assert.equal(canEdit('alice', 'alice'), true);
    assert.equal(canEdit('alice', 'bob'), false);
  });
  it('query builder caps paging like the backend', () => {
    assert.equal(listParams('Pump', 2, 500), 'search=Pump&page=2&per_page=50');
    assert.equal(listParams('', 0, 0), 'page=1&per_page=1');
  });
});
