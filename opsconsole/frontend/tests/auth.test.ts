import { strict as assert } from 'node:assert';
import { describe, it } from 'node:test';
import { can, cancelAllowed, retryAllowed } from '../src/auth.ts';

describe('auth matrix (mirrors backend)', () => {
  it('viewer is read-only', () => {
    assert.equal(can('viewer', 'retry'), false);
    assert.equal(can('viewer', 'cancel'), false);
    assert.equal(can('viewer', 'act'), false);
    assert.equal(can('viewer', 'audit'), false);
  });
  it('operator mutates but sees no audit', () => {
    assert.equal(can('operator', 'retry'), true);
    assert.equal(can('operator', 'cancel'), true);
    assert.equal(can('operator', 'act'), true);
    assert.equal(can('operator', 'audit'), false);
  });
  it('admin does everything', () => {
    for (const a of ['retry', 'cancel', 'act', 'audit'] as const) {
      assert.equal(can('admin', a), true);
    }
  });
  it('status rules match backend 422s', () => {
    assert.equal(retryAllowed('failed'), true);
    assert.equal(retryAllowed('done'), false);
    assert.equal(cancelAllowed('queued'), true);
    assert.equal(cancelAllowed('running'), true);
    assert.equal(cancelAllowed('failed'), false);
    assert.equal(cancelAllowed('done'), false);
  });
});
