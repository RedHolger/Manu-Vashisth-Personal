import { strict as assert } from 'node:assert';
import { spawn, type ChildProcess } from 'node:child_process';
import { after, before, describe, it } from 'node:test';
import { actWithRetry, api, isAmbiguous, makeKey, setBase, setRole } from '../src/api.ts';

const PORT = 18081;
let server: ChildProcess;

async function waitReady(): Promise<void> {
  for (let i = 0; i < 100; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${PORT}/api/jobs`);
      if (r.ok) return;
    } catch {
      /* not up yet */
    }
    await new Promise((r) => setTimeout(r, 100));
  }
  throw new Error('backend never came up');
}

describe('frontend client cancel integration (live backend)', () => {
  before(async () => {
    server = spawn('python3', ['backend/server.py', String(PORT)], {
      cwd: new URL('.', import.meta.url).pathname.replace(/\/frontend\/tests\/?$/, ''),
    });
    await waitReady();
    setBase(`http://127.0.0.1:${PORT}`);
    setRole('operator');
  });
  after(() => server.kill());

  it('cancel sends the required key (was HTTP 400)', async () => {
    const key = makeKey('cancel', 6, 1);
    const first: any = await api.cancel(6, 1, key);
    assert.equal(first.job.status, 'canceled');
    const job: any = await api.job(6);
    assert.equal(job.version, 2); // exactly one mutation
  });

  it('repeating the same logical cancel replays (no second mutation)', async () => {
    const key = makeKey('cancel', 6, 1);
    const again: any = await api.cancel(6, 1, key);
    assert.equal(again.replayed, true);
    const job: any = await api.job(6);
    assert.equal(job.version, 2);
  });

  it('actWithRetry reuses the stable key on the retry path', async () => {
    const a: any = await actWithRetry('retry', 1, 1);
    assert.equal(a.retried, false);
    const b: any = await actWithRetry('retry', 1, 1);
    assert.equal(b.body.run_id, a.body.run_id); // same key -> same run
  });
});

describe('key policy units', () => {
  it('makeKey is stable per logical action', () => {
    assert.equal(makeKey('cancel', 6, 1), makeKey('cancel', 6, 1));
    assert.notEqual(makeKey('cancel', 6, 1), makeKey('cancel', 6, 2));
    assert.notEqual(makeKey('cancel', 6, 1), makeKey('retry', 6, 1));
  });

  it('isAmbiguous: network/5xx retry, 4xx decisive', () => {
    assert.equal(isAmbiguous(new TypeError('fetch failed')), true);
    assert.equal(isAmbiguous(new Error('500: boom')), true);
    assert.equal(isAmbiguous(new Error('503: down')), true);
    assert.equal(isAmbiguous(new Error('400: bad')), false);
    assert.equal(isAmbiguous(new Error('409: stale version')), false);
    assert.equal(isAmbiguous(new Error('403: forbidden')), false);
  });
});
