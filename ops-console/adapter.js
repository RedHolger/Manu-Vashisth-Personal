'use strict';
// P13-01 export adapter: real run-evidence JSON -> incident rows.
//
// Honesty rule: the adapter NEVER invents incident lifecycle. Machine outputs
// carry no review status, so adapted rows get state 'UNKNOWN' (needs review)
// with provenance (source file + sha256). Only explicitly labeled SYNTHETIC
// fixtures use OPEN/VERIFYING/RESOLVED. Missing telemetry stays UNKNOWN — a
// recovered incident is never fabricated from it.
const fs = require('node:fs');
const crypto = require('node:crypto');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '..');

function sha256File(relpath) {
  const abs = path.join(ROOT, relpath);
  if (!fs.existsSync(abs)) throw new Error('export missing: ' + relpath);
  return crypto.createHash('sha256').update(fs.readFileSync(abs)).digest('hex');
}

function adaptVerificationRun(obj, relpath) {
  // Maps a real detection-evaluation object (e.g. P12 metrics.json) to rows.
  // Each per-scenario outcome becomes one row; state is UNKNOWN (unreviewed).
  const sha = sha256File(relpath);
  const at = new Date().toISOString();
  const rows = [];
  const fps = obj.benign_lookalike_false_positives || {};
  for (const [sid, entry] of Object.entries(fps)) {
    rows.push({
      id: 'verification-' + sid,
      service: 'detection-evaluation',
      state: 'UNKNOWN',
      updated: at,
      events: [{ at,
        text: 'Benign look-alike; flagged=' + entry.flagged +
              '; rationale: ' + (entry.benign_rationale || 'n/a').slice(0, 160) }],
      provenance: { source: relpath, sha256: sha, kind: 'verification-run' },
    });
  }
  const per = obj.per_detector || obj.perDetector || {};
  for (const [detector, stats] of Object.entries(per)) {
    rows.push({
      id: 'verification-detector-' + detector,
      service: 'detection-evaluation',
      state: 'UNKNOWN',
      updated: at,
      events: [{ at, text: 'Detector summary: ' + JSON.stringify(stats).slice(0, 200) }],
      provenance: { source: relpath, sha256: sha, kind: 'verification-run' },
    });
  }
  if (!rows.length) throw new Error('no mappable outcomes in ' + relpath);
  return rows;
}

function adaptSynthetic() {
  const now = new Date().toISOString();
  return [{
    id: 'synthetic-1', service: 'reservations', state: 'VERIFYING',
    updated: now,
    events: [{ at: now, text: 'Synthetic fixture: waiting for three healthy windows.' }],
    provenance: { source: 'synthetic-fixture', kind: 'synthetic' },
  }];
}

function pendingGate() {
  return { status: 'BLOCKED',
    awaiting: 'real P01-P03 live SRE run exports (healthy + error windows)',
    note: 'Adapter reads real portfolio run-evidence today; live SRE telemetry needs lab access + read-only Prometheus URL. Missing telemetry renders UNKNOWN, never a fabricated incident.' };
}

module.exports = { adaptVerificationRun, adaptSynthetic, pendingGate, sha256File };
