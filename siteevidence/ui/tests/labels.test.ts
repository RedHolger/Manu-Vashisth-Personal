import { strict as assert } from 'node:assert';
import { describe, it } from 'node:test';
import { bucketByOwner, dueLabel, isOverdue } from '../src/labels.ts';

const T = '2026-10-08'; // frozen demo date

describe('site labels', () => {
  it('overdue logic mirrors backend', () => {
    assert.equal(isOverdue('open', '2026-09-20', T), true);
    assert.equal(isOverdue('open', '2026-10-15', T), false);
    assert.equal(isOverdue('answered', '2026-09-20', T), false);
    assert.equal(isOverdue('open', T, T), false);
  });
  it('labels', () => {
    assert.equal(dueLabel('open', '2026-09-20', T), 'OVERDUE since 2026-09-20');
    assert.equal(dueLabel('open', T, T), 'due today');
    assert.equal(dueLabel('closed', '2026-09-20', T), 'closed');
  });
  it('owner buckets count open only', () => {
    const rfis = [
      { id: 'a', title: '', owner: 'AO', due: '', status: 'open', rev: 1 },
      { id: 'b', title: '', owner: 'AO', due: '', status: 'closed', rev: 1 },
      { id: 'c', title: '', owner: 'BK', due: '', status: 'open', rev: 1 },
    ];
    assert.deepEqual(bucketByOwner(rfis), { AO: 1, BK: 1 });
  });
});
