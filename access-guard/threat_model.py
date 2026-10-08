"""Threat-model auditor for AccessGuard (P11-04).

`audit_threat_model()` verifies that `THREAT_MODEL.md` keeps its honesty
guarantees: the required sections exist, the no-universal-security disclaimer
is present verbatim, no affirmative universal-security phrase slipped in,
coverage is reported with counts (not bare adjectives), and residual risks
are listed. It is a documentation guard, not a security proof.
"""
from pathlib import Path

DISCLAIMER = 'Finite cases do not prove universal security'
REQUIRED_SECTIONS = ['## Scope', '## Trusted boundaries',
                     '## Supported attacker capabilities',
                     '## Unsupported attacker capabilities',
                     '## Residual risks',
                     '## What this evidence does not prove']
FORBIDDEN_PHRASES = ['provably secure', 'guaranteed secure', 'fully secure',
                     'no vulnerabilities', 'impossible to bypass',
                     'complete security', 'military-grade', 'unbreakable',
                     '100% secure', 'bulletproof']
COVERAGE_FACTS = ['22-case', '7 mismatches', '0 mismatches', '4 planted']


def _section_body(text, heading):
    start = text.find(heading)
    if start < 0:
        return ''
    end = len(text)
    for other in REQUIRED_SECTIONS:
        if other == heading:
            continue
        pos = text.find(other, start + len(heading))
        if 0 < pos < end:
            end = pos
    return text[start:end]


def audit_threat_model(doc_path='THREAT_MODEL.md'):
    text = Path(doc_path).read_text(encoding='utf-8')
    lowered = text.lower()
    checks = {}
    checks['required_sections_present'] = all(
        s in text for s in REQUIRED_SECTIONS)
    checks['disclaimer_present_twice'] = (
        text.count(DISCLAIMER) >= 2)
    checks['no_universal_security_claim'] = not any(
        phrase in lowered for phrase in FORBIDDEN_PHRASES)
    checks['coverage_reported_with_counts'] = all(
        fact in text for fact in COVERAGE_FACTS)
    residual = _section_body(text, '## Residual risks')
    numbered = [ln for ln in residual.splitlines()
                if ln.strip() and ln.strip()[0].isdigit()
                and ln.strip()[1:2] == '.']
    checks['residual_risks_listed'] = len(numbered) >= 3
    checks['scope_names_the_harness'] = (
        'policy_oracle.py' in text and 'lab_app.py' in text
        and 'runner.py' in text)
    return {'checks': checks, 'all_ok': all(checks.values()),
            'disclaimer_count': text.count(DISCLAIMER),
            'residual_items': len(numbered)}
