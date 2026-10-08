"""Remediation replay for IncidentReplay (P12-04): the hardened service model.

The "hardened local service" in this synthetic workbench is the deterministic
scenario generator itself, with two substantive controls applied. The SAME
scenario scripts run against the ORIGINAL and the HARDENED generator; the
identical ingest -> detect -> score pipeline scores both; original and
repaired outcomes are retained side by side. Detectors are NEVER retuned
here — `detect.configuration()` must be byte-identical across both runs, so
any change in findings is remediation effect, not threshold tuning.

Controls (both deterministic, no randomness, no clock reads):

* **R1 — MFA for interactive logins.** An interactive `login` success whose
  factors are password-only (``set(factors) <= {'password'}``) is REJECTED by
  the hardened service and logged as a failure
  (``action='login_denied_mfa'``). Workload/service sessions are out of scope
  and untouched; MFA logins (password+totp) still succeed.
* **R2 — ticketed bulk egress.** A data-plane read (`download`/`export`) of
  >= 10 MB without a `ticket_ref` is DENIED (logged as
  ``action='egress_denied_no_ticket'`` with `bytes_out=0`; the attempt stays
  in the log for audit). Ticketed bulk and small unticketed reads pass.

Event ids, seq numbers, rotation-loss omissions, origins, timestamps and the
baselines are preserved, so ground truth still maps and the only difference
between the two corpora is what the controls bit.
"""
import hashlib
import json
from pathlib import Path

import scenarios

R1_MFA_INTERACTIVE = 'R1'
R2_TICKETED_BULK_EGRESS = 'R2'
CONTROLS = (R1_MFA_INTERACTIVE, R2_TICKETED_BULK_EGRESS)

R2_BYTES_THRESHOLD = 10_000_000
DATA_PLANE_ACTIONS = ('download', 'export')

REMEDIATION_MD = """# Hardened-service model — P12-04 remediation replay

The hardened corpus in this directory was produced by `harden.py` from the
SAME scenario scripts as `fixtures/`, with two controls applied. Detectors
and thresholds are UNCHANGED; any finding delta is remediation effect.

## R1 — MFA for interactive logins

Interactive `login` successes with password-only factors are rejected
(`login_denied_mfa`, logged as failures). Workload sessions and MFA
(password+totp) logins are unaffected.

## R2 — ticketed bulk egress (>= 10 MB)

Unticketed `download`/`export` events of >= 10 MB are denied
(`egress_denied_no_ticket`, bytes zeroed, attempt retained for audit).
Ticketed bulk and small unticketed reads pass.

## What this is and is not

- IS: a deterministic model of two service-side controls, replayed through
  the identical ingest/detect/score pipeline, with original and repaired
  outcomes retained.
- IS NOT: a production deployment, a detector retune, or measured defender
  time. No thresholds were moved to flatter a metric.
"""


def _is_password_only(factors):
    return set(factors or []) <= {'password'}


def apply_controls(events, controls=CONTROLS):
    """Return ``(hardened_events, applied)``; ids/seq/omissions preserved."""
    controls = tuple(controls)
    hardened, applied = [], []
    for event in events:
        event = dict(event)
        fired = []
        if (R1_MFA_INTERACTIVE in controls
                and event['kind'] == 'success'
                and event['action'] == 'login'
                and event.get('session_type') == 'interactive'
                and _is_password_only(event.get('auth_factors'))):
            event['kind'] = 'failure'
            event['action'] = 'login_denied_mfa'
            fired.append(R1_MFA_INTERACTIVE)
        if (R2_TICKETED_BULK_EGRESS in controls
                and event['action'] in DATA_PLANE_ACTIONS
                and not event.get('ticket_ref')
                and int(event.get('bytes_out', 0)) >= R2_BYTES_THRESHOLD):
            event['action'] = 'egress_denied_no_ticket'
            event['bytes_out'] = 0
            fired.append(R2_TICKETED_BULK_EGRESS)
        if fired:
            applied.append({'id': event['id'], 'controls': fired})
        hardened.append(event)
    return hardened, applied


def harden_scenario(scenario_id, controls=CONTROLS):
    """Hardened logical events + baseline + applied-control record."""
    events, baseline = scenarios.logical_events(scenario_id)
    hardened, applied = apply_controls(events, controls)
    return hardened, baseline, applied


def write_hardened_scenario(scenario_id, root, controls=CONTROLS):
    """Serialize one hardened scenario (same layout as `scenario_files`)."""
    root = Path(root)
    events, baseline = scenarios.logical_events(scenario_id)
    hardened, applied = apply_controls(events, controls)
    directory = root / scenario_id
    directory.mkdir(parents=True, exist_ok=True)

    written = [e for e in hardened if not e['omit_from_files']]
    audit_events = [e for e in written
                    if e['origin'] in ('audit', 'audit+syslog')]
    syslog_events = [e for e in written
                     if e['origin'] in ('audit+syslog', 'syslog')]
    rows = []
    audit = directory / 'audit.jsonl'
    audit.write_text(''.join(
        json.dumps(scenarios._json_record(e), sort_keys=True) + '\n'
        for e in audit_events), encoding='utf-8')
    rows.append(scenarios._file_row(audit, 'json-audit', scenario_id,
                                    len(audit_events)))
    if syslog_events:
        syslog = directory / 'edge-syslog.log'
        syslog.write_text(''.join(scenarios.syslog_line(e) + '\n'
                                  for e in syslog_events), encoding='utf-8')
        rows.append(scenarios._file_row(syslog, 'syslog-kv', scenario_id,
                                        len(syslog_events)))
    baseline_path = directory / 'baseline.json'
    baseline_path.write_text(json.dumps(
        dict(baseline, scenario=scenario_id,
             source='asset-owner configuration (synthetic)',
             note='detector input, not a label'),
        indent=2, sort_keys=True) + '\n', encoding='utf-8')
    rows.append(scenarios._file_row(baseline_path, 'baseline-config',
                                    scenario_id, 0))
    return rows, applied


def write_hardened_fixtures(root, controls=CONTROLS):
    """Materialize the hardened corpus + manifest + remediation note."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    rows, applied_by_scenario = [], {}
    for scenario_id in scenarios.SCENARIO_IDS:
        file_rows, applied = write_hardened_scenario(scenario_id, root,
                                                     controls)
        rows.extend(file_rows)
        applied_by_scenario[scenario_id] = applied
    (root / 'REMEDIATION.md').write_text(REMEDIATION_MD, encoding='utf-8')
    manifest = {'generated_by': 'harden.write_hardened_fixtures()',
                'synthetic': True, 'real_incident': False,
                'controls': list(controls),
                'r2_bytes_threshold': R2_BYTES_THRESHOLD,
                'files': rows,
                'applied_controls': applied_by_scenario,
                'corpus_sha256': hashlib.sha256(
                    '\n'.join(r['sha256'] for r in rows).encode()
                ).hexdigest()}
    (root / 'manifest.json').write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + '\n',
        encoding='utf-8')
    return manifest


def control_summary():
    return {'controls': list(CONTROLS),
            'R1': 'MFA for interactive logins (password-only rejected)',
            'R2': 'ticketed bulk egress >= %d bytes (unticketed denied)'
                  % R2_BYTES_THRESHOLD}
