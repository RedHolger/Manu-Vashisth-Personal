'use strict';
// P13-02 robustness contract (node-testable): large lists, URL state,
// import-failure preservation, stale/future timestamps.
const model = require('./model.js');

const RENDER_LIMIT = 500;

function sliceList(rows, limit = RENDER_LIMIT) {
  // Large-list behavior without a DOM: cap rendered rows, report truncation.
  const hits = rows.slice(0, limit);
  return { rendered: hits, total: rows.length,
           truncated: rows.length - hits.length };
}

function parseUrlState(url) {
  const params = new URL(url, 'http://localhost').searchParams;
  const q = params.get('q') || '';
  const raw = params.get('state') || 'ALL';
  const state = ['ALL', 'OPEN', 'VERIFYING', 'RESOLVED', 'UNKNOWN']
    .includes(raw) ? raw : 'ALL';
  return { q, state };
}

function serializeUrlState(q, state) {
  const params = new URLSearchParams({ q, state });
  return '/?' + params.toString();
}

function importState(current, text) {
  // Failed imports preserve previous rows (never blank the viewer).
  try {
    if (Buffer.byteLength(text, 'utf8') > 2000000) {
      throw new Error('Maximum file size is 2 MB');
    }
    const rows = model.validate(JSON.parse(text));
    return { rows, error: null };
  } catch (err) {
    return { rows: current, error: String(err.message || err) };
  }
}

function freshnessBucket(row, now) {
  // Surfaces stale/future explicitly (CLOCK_SKEW), never as current.
  return model.freshness(row, now);
}

module.exports = { sliceList, parseUrlState, serializeUrlState, importState,
  freshnessBucket, RENDER_LIMIT };
