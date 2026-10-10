import { strict as assert } from 'node:assert';
import { describe, it } from 'node:test';
import { clampPage, pageSlice, totalPages } from '../src/paging.ts';

describe('paging helpers', () => {
  it('page counts', () => {
    assert.equal(totalPages(12, 5), 3);
    assert.equal(totalPages(0, 5), 1);
    assert.throws(() => totalPages(12, 0));
  });
  it('clamps', () => {
    assert.equal(clampPage(99, 12, 5), 3);
    assert.equal(clampPage(0, 12, 5), 1);
    assert.equal(clampPage(2, 12, 5), 2);
  });
  it('slices match backend windowing', () => {
    const items = Array.from({ length: 12 }, (_, i) => i + 1);
    assert.deepEqual(pageSlice(items, 2, 5), [6, 7, 8, 9, 10]);
    assert.deepEqual(pageSlice(items, 99, 5), [11, 12]);
  });
});
