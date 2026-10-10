import { strict as assert } from 'node:assert';
import { describe, it } from 'node:test';
import { driftLabel, groupByStatus } from '../src/view.ts';

describe('view helpers', () => {
  it('drift labels', () => {
    assert.equal(driftLabel(3), '+3d late');
    assert.equal(driftLabel(-2), '2d buffer');
    assert.equal(driftLabel(0), 'on track');
  });
  it('status groups', () => {
    const tasks = {
      T1: { status: 'done', title: '', team: '', owner: '', start: '', dur: 1, deps: [] },
      T2: { status: 'queued', title: '', team: '', owner: '', start: '', dur: 1, deps: [] },
    } as any;
    assert.deepEqual(groupByStatus(['T1', 'T2'], tasks).done, ['T1']);
    assert.deepEqual(groupByStatus(['T1', 'T2'], tasks).queued, ['T2']);
  });
});
