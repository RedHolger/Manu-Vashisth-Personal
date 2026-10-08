"""Ground-truth scoring for IncidentReplay (P12-02).

Scoring happens at two levels, and **both always report raw counts** next to
any ratio, because a precision of 1.0 over one scenario is not the same claim
as a precision of 1.0 over four:

* **Scenario level** — was the scenario flagged at all? Yields TP/FP/FN/TN
  over the labeled set, precision, recall, F1 and accuracy. This is the level
  the acceptance gate names ("precision/recall with counts").
* **Event level** — of the event ids a detector cited as evidence, how many
  are annotated attack events, and how many annotated attack events did it
  reach? This exposes what a scenario-level true positive hides: a rule can
  flag the right scenario while citing evidence that is mostly benign.

Scenarios are scored on the fixed hashed dev/held-out split from
`scenarios.split()` and every metric is reported per split as well as over the
whole corpus, so the held-out numbers cannot be averaged away.

Labels are read only through `groundtruth.reveal`. Nothing in this module is
handed to a detector.
"""
import detect
import groundtruth
import scenarios
from ingest import Ingestor

COMBINED = 'ANY'


def load_corpus(root=None, tolerance=scenarios.CLOCK_SKEW_TOLERANCE_SECONDS):
    """Ingest every scenario once; returns ``{sid: {timeline, baseline}}``."""
    ingestor = Ingestor(clock_skew_tolerance_seconds=tolerance)
    corpus = {}
    for scenario_id in scenarios.SCENARIO_IDS:
        corpus[scenario_id] = {
            'timeline': ingestor.ingest_scenario(scenario_id, root),
            'baseline': scenarios.load_baseline(scenario_id, root)}
    return corpus


def run_detectors(corpus, names=None):
    """``{sid: {detector: [finding, ...]}}`` — labels are never passed in."""
    names = detect.detector_names() if names is None else list(names)
    return {sid: detect.run_all(entry['timeline'].events, sid,
                                entry['baseline'], names)
            for sid, entry in corpus.items()}


def _ratio(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else None


def _f1(precision, recall):
    if precision is None or recall is None:
        return None
    if precision + recall == 0:
        return 0.0
    return round(2 * precision * recall / (precision + recall), 4)


def scenario_metrics(flagged_ids, scenario_ids, revealed):
    """TP/FP/FN/TN over scenarios, with the ids behind every count."""
    flagged_ids = set(flagged_ids)
    buckets = {'tp': [], 'fp': [], 'fn': [], 'tn': []}
    for sid in scenario_ids:
        malicious = revealed[sid]['malicious']
        flagged = sid in flagged_ids
        if malicious and flagged:
            buckets['tp'].append(sid)
        elif flagged:
            buckets['fp'].append(sid)
        elif malicious:
            buckets['fn'].append(sid)
        else:
            buckets['tn'].append(sid)
    precision = _ratio(len(buckets['tp']),
                       len(buckets['tp']) + len(buckets['fp']))
    recall = _ratio(len(buckets['tp']),
                    len(buckets['tp']) + len(buckets['fn']))
    total = len(scenario_ids)
    return {'tp': len(buckets['tp']), 'fp': len(buckets['fp']),
            'fn': len(buckets['fn']), 'tn': len(buckets['tn']),
            'n_scenarios': total,
            'n_malicious': sum(1 for sid in scenario_ids
                               if revealed[sid]['malicious']),
            'n_benign': sum(1 for sid in scenario_ids
                            if not revealed[sid]['malicious']),
            'precision': precision, 'recall': recall,
            'f1': _f1(precision, recall),
            'accuracy': _ratio(len(buckets['tp']) + len(buckets['tn']), total),
            'tp_ids': sorted(buckets['tp']), 'fp_ids': sorted(buckets['fp']),
            'fn_ids': sorted(buckets['fn']), 'tn_ids': sorted(buckets['tn'])}


def event_metrics(findings_by_scenario, scenario_ids, revealed, corpus):
    """Evidence-level counts: what was cited, and what was actually attack."""
    per_scenario, emitted, on_attack, on_benign = {}, 0, 0, 0
    annotated_total = citable_total = 0
    cited_attack = set()
    for sid in scenario_ids:
        annotated = set(revealed[sid]['attack_event_ids'])
        present = corpus[sid]['timeline'].ids()
        citable = annotated & present
        annotated_total += len(annotated)
        citable_total += len(citable)
        cited = set()
        for finding in findings_by_scenario.get(sid, []):
            cited.update(finding['evidence_ids'])
        emitted += len(cited)
        true_ids = sorted(cited & annotated)
        false_ids = sorted(cited - annotated)
        on_attack += len(true_ids)
        on_benign += len(false_ids)
        cited_attack |= citable & cited
        per_scenario[sid] = {
            'malicious': revealed[sid]['malicious'],
            'attack_events_annotated': len(annotated),
            'attack_events_in_evidence': len(citable),
            'attack_events_absent': sorted(annotated - present),
            'evidence_ids_cited': len(cited),
            'evidence_ids_on_attack': len(true_ids),
            'evidence_ids_not_on_attack': len(false_ids),
            'cited_attack_ids': true_ids,
            'cited_non_attack_ids': false_ids,
            'missed_attack_ids': sorted(citable - cited)}
    return {'attack_events_annotated': annotated_total,
            'attack_events_in_evidence': citable_total,
            'attack_events_absent_from_sources':
                annotated_total - citable_total,
            'evidence_ids_cited': emitted,
            'evidence_ids_on_attack': on_attack,
            'evidence_ids_not_on_attack': on_benign,
            'evidence_precision': _ratio(on_attack, emitted),
            'attack_coverage': _ratio(len(cited_attack), citable_total),
            'attack_events_reached': len(cited_attack),
            'per_scenario': per_scenario}


def benign_false_positives(findings, scenario_ids, revealed):
    """Which detectors fired on which benign look-alike, and on what."""
    report = {}
    for sid in scenario_ids:
        if revealed[sid]['malicious']:
            continue
        per_detector = findings.get(sid, {})
        fired = {name: [sorted(finding['evidence_ids'])
                        for finding in per_detector.get(name, [])]
                 for name in sorted(per_detector) if per_detector.get(name)}
        report[sid] = {
            'benign_lookalike_of': revealed[sid]['benign_lookalike_of'],
            'benign_rationale': revealed[sid]['benign_rationale'],
            'flagged_by': sorted(fired),
            'false_positive': bool(fired),
            'false_positive_evidence_ids': fired}
    return report


def _flagged_for(findings, name, scenario_ids):
    if name == COMBINED:
        return detect.union_flagged(
            {sid: findings[sid] for sid in scenario_ids})
    return detect.flagged({sid: findings[sid] for sid in scenario_ids}, name)


def _evidence_view(findings, name, scenario_ids):
    """Findings attributable to one detector (or to the combined policy)."""
    view = {}
    for sid in scenario_ids:
        if name == COMBINED:
            view[sid] = [finding
                         for detector in sorted(findings[sid])
                         for finding in findings[sid][detector]]
        else:
            view[sid] = list(findings[sid].get(name, []))
    return view


def evaluate(corpus=None, findings=None, names=None):
    """Full evaluation report: per detector, per split, both levels."""
    names = detect.detector_names() if names is None else list(names)
    corpus = load_corpus() if corpus is None else corpus
    findings = run_detectors(corpus, names) if findings is None else findings
    partition = scenarios.split()
    revealed = groundtruth.reveal(scenarios.SCENARIO_IDS)
    scored = list(names) + [COMBINED]

    per_detector = {}
    for name in scored:
        splits = {'all': scenarios.SCENARIO_IDS, 'dev': partition['dev'],
                  'held_out': partition['held_out']}
        per_detector[name] = {
            'kind': ('combined' if name == COMBINED
                     else detect.DETECTOR_KIND[name]),
            'description': ('flagged by at least one detector'
                            if name == COMBINED
                            else detect.DETECTOR_DESCRIPTIONS[name]),
            'scenario_level': {
                split: scenario_metrics(
                    _flagged_for(findings, name, ids), ids, revealed)
                for split, ids in splits.items()},
            'event_level': {
                split: event_metrics(_evidence_view(findings, name, ids),
                                     ids, revealed, corpus)
                for split, ids in splits.items()}}

    return {'corpus': {'scenarios': list(scenarios.SCENARIO_IDS),
                       'split': partition,
                       'events': sum(len(entry['timeline'].events)
                                     for entry in corpus.values()),
                       'fixture_corpus_sha256': scenarios.write_fixtures()[
                           'corpus_sha256']},
            'detector_configuration': detect.configuration(),
            'labels': {sid: {'malicious': revealed[sid]['malicious'],
                             'attack_kind': revealed[sid]['attack_kind'],
                             'benign_lookalike_of':
                                 revealed[sid]['benign_lookalike_of'],
                             'attack_events':
                                 len(revealed[sid]['attack_event_ids'])}
                       for sid in sorted(revealed)},
            'per_detector': per_detector,
            'benign_lookalike_false_positives': benign_false_positives(
                findings, scenarios.SCENARIO_IDS, revealed),
            'findings': {sid: {name: findings[sid].get(name, [])
                               for name in names}
                         for sid in sorted(findings)}}


def summary_lines(report):
    """Human-readable one-line-per-detector summary (raw counts first)."""
    lines = []
    for name, block in sorted(report['per_detector'].items()):
        for split in ('all', 'dev', 'held_out'):
            metrics = block['scenario_level'][split]
            lines.append(
                '%-24s %-9s TP=%d FP=%d FN=%d TN=%d  precision=%s recall=%s '
                'f1=%s' % (name, split, metrics['tp'], metrics['fp'],
                           metrics['fn'], metrics['tn'],
                           metrics['precision'], metrics['recall'],
                           metrics['f1']))
    return lines


LABEL_API_NAMES = ('GROUND_TRUTH', 'reveal', 'is_malicious',
                   'attack_event_ids', 'malicious_ids', 'benign_ids',
                   'attack_totals')


def label_isolation_audit(modules=('detect.py', 'ingest.py')):
    """Prove the evidence/detector import graph cannot reach the labels.

    Parses each module with ``ast`` — including imports nested inside
    functions — and reports the import set plus any reference to the label
    API. A docstring may *describe* the separation; only the code is audited.
    """
    import ast
    from pathlib import Path
    audit = {}
    for name in modules:
        tree = ast.parse(Path(name).read_text(encoding='utf-8'))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        used = {node.id for node in ast.walk(tree)
                if isinstance(node, ast.Name)}
        used |= {node.attr for node in ast.walk(tree)
                 if isinstance(node, ast.Attribute)}
        audit[name] = {'imports': sorted(imported),
                       'imports_groundtruth': 'groundtruth' in imported,
                       'label_api_references': sorted(
                           used & set(LABEL_API_NAMES))}
    return audit


def findings_are_label_independent(corpus, findings):
    """Re-run every detector with all labels inverted; findings must not move.

    This is the behavioural companion to :func:`label_isolation_audit`: an
    import-graph audit can be defeated by a dynamic lookup, so the labels are
    actually flipped and the detector output is compared.
    """
    original = {sid: entry['malicious']
                for sid, entry in groundtruth.GROUND_TRUTH.items()}
    try:
        for entry in groundtruth.GROUND_TRUTH.values():
            entry['malicious'] = not entry['malicious']
        inverted = groundtruth.malicious_ids()
        again = run_detectors(corpus)
    finally:
        for sid, value in original.items():
            groundtruth.GROUND_TRUTH[sid]['malicious'] = value
    return {'findings_identical_under_inverted_labels': again == findings,
            'malicious_ids_while_inverted': inverted,
            'malicious_ids_restored': groundtruth.malicious_ids()}
