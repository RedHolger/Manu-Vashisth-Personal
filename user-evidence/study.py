"""Session capture, analysis and retest tooling for UserEvidence (P15-02..04).

All human gates are BLOCKED (no consenting participants), so this module is
the *instrument* — consent-gated capture, contradiction-retaining analysis
and disclaimer-bound retest comparison — verified on synthetic fixtures and
ready for real sessions. It refuses to fabricate: human records need consent,
PII-unchecked records are rejected, and population claims raise.
"""
import project


class ConsentError(RuntimeError):
    pass


class FabricationError(RuntimeError):
    pass


class PopulationClaimError(RuntimeError):
    pass


def _scrubbed(text):
    """Redact email/phone shapes; return (text, had_pii)."""
    import re
    redacted, n1 = re.subn(r'[\w.+-]+@[\w-]+\.[\w.]+', '[email]', text)
    redacted, n2 = re.subn(r'\d{7,}', '[number]', redacted)
    return redacted, (n1 + n2) > 0


class SessionCapture:
    """Consent-gated, pseudonymous session recorder."""

    def __init__(self):
        self.sessions = []
        self._counter = 0

    def _next_id(self):
        self._counter += 1
        return 'P-%03d' % self._counter

    def record(self, task, success, seconds, observation, codes=(),
               consent=None, synthetic=False, pii_checked=False):
        """Record one session row. Human rows need consent + a PII check;
        synthetic fixtures are tagged and excluded from human metrics."""
        if not synthetic:
            if not (consent and consent.get('granted')):
                raise ConsentError('human session without consent refused')
            if not pii_checked:
                raise ConsentError('PII check required before storing')
            human = True
        else:
            human = False
        observation, had_pii = _scrubbed(observation)
        if had_pii and human:
            raise ConsentError('PII detected in observation; re-check refused')
        # Pseudonyms are assigned only after every refusal gate passes, so a
        # refused attempt never consumes an id and leaves a gap.
        participant = self._next_id() if human else \
            'synthetic-%02d' % (len(self.sessions) + 1)
        row = {'participant': participant, 'task': task, 'success': bool(success),
               'seconds': seconds, 'observation': observation,
               'codes': list(codes), 'synthetic': (not human)}
        project.summarize([row])  # schema validation; raises on bad rows
        self.sessions.append(row)
        return row

    def human_sessions(self):
        return [s for s in self.sessions if not s['synthetic']]

    def synthetic_sessions(self):
        return [s for s in self.sessions if s['synthetic']]


class Analysis:
    """Code observations; keep contradictions; separate counts."""

    def __init__(self, sessions):
        self.sessions = list(sessions)
        self.notes = {}          # (participant, task) -> analyst_note
        self.second_coder = []   # reviewed sample rows (empty = pending)

    def annotate(self, participant, task, note):
        """Attach an interpretation WITHOUT touching the verbatim observation."""
        key = (participant, task)
        if key in self.notes:
            raise ValueError('note already exists; interpretations append, '
                             'never overwrite (use a new key)')
        if not any(s['participant'] == participant and s['task'] == task
                   for s in self.sessions):
            raise KeyError('no such session')
        self.notes[key] = note
        return note

    def contradictions(self):
        """Codes with both successful and failed outcomes — retained, listed."""
        by_code = {}
        for s in self.sessions:
            for code in set(s['codes']):
                by_code.setdefault(code, {'success': [], 'fail': []})
                by_code[code]['success' if s['success'] else 'fail'].append(
                    (s['participant'], s['task']))
        return {c: v for c, v in by_code.items() if v['success'] and v['fail']}

    def counts(self):
        participants = {s['participant'] for s in self.sessions}
        return {'participants': len(participants),
                'observations': len(self.sessions),
                'human_participants': len(
                    {s['participant'] for s in self.sessions
                     if not s['synthetic']})}

    def task_summary(self):
        return project.summarize(self.sessions)

    def mark_second_coder_review(self, sample_keys, reviewer):
        for key in sample_keys:
            if key not in [(s['participant'], s['task']) for s in self.sessions]:
                raise KeyError('sample key %r is not a real session' % (key,))
        self.second_coder = [{'session': k, 'reviewer': reviewer}
                             for k in sample_keys]
        return self.second_coder


class Retest:
    """Before/after comparison on matched tasks, with a built-in disclaimer."""

    DISCLAIMER = ('convenience sample; formative only; no population, causal '
                  'or generalizable claim')

    def __init__(self, before_rows, after_rows):
        self.before = list(before_rows)
        self.after = list(after_rows)

    def compare(self):
        before = project.summarize(self.before)['tasks']
        after = project.summarize(self.after)['tasks']
        matched = sorted(set(before) & set(after))
        if not matched:
            raise ValueError('no matched tasks; comparison refused')
        delta = {}
        for task in matched:
            b, a = before[task], after[task]
            delta[task] = {'completed_before': b['completed'],
                           'completed_after': a['completed'],
                           'median_seconds_before': b['median_seconds'],
                           'median_seconds_after': a['median_seconds'],
                           'n_before': b['n'], 'n_after': a['n']}
        return {'matched_tasks': matched, 'delta': delta,
                'disclaimer': self.DISCLAIMER}

    def claim(self, kind):
        if kind in ('population', 'generalize', 'causal'):
            raise PopulationClaimError(
                'a %s claim from a convenience sample is refused' % kind)
        raise ValueError('unknown claim kind %r' % (kind,))
