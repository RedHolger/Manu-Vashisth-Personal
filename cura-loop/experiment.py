"""Fair active-learning comparison for CuraLoop (P10-03).

Runs random, uncertainty and diversity selection on the *same* P10-01 entity
pool, under a matched budget, matched seeds and a matched initial labeled
subset, so the only difference between curves is the selection rule. Labels
are acquired through the query-logged Oracle and accounted for by the P10-02
versioned store. Held-out test features are used only on the evaluation path;
a selector's inputs are asserted to contain no test id, so selection cannot
use test results.

Output is dependency-free: raw per-seed learning curves (CSV), a summary
(JSON) and an SVG line chart of the seed-averaged curves. Simulated labeling
cost is a wall-clock/acquisition proxy, never measured human time.
"""
import csv
import hashlib
import io
import random

from annotation import AnnotationStore, Budget
from pool import build, test_features
from project import probability, select

METHODS = ('random', 'uncertainty', 'diversity')
_COLORS = {'random': '#888888', 'uncertainty': '#1f77b4',
           'diversity': '#d62728'}


def _initial_ids(pool_items, seed, k):
    """Seed-derived initial labeled subset — identical for every method."""
    init = random.Random(seed + 1)
    return init.sample([it['id'] for it in pool_items], min(k, len(pool_items)))


def _accuracy(labeled, test_x, test_labels):
    if not test_x:
        return 0.0
    correct = 0
    for tid, x in test_x.items():
        pred = int(probability(x, labeled) >= 0.5)
        correct += int(pred == test_labels[tid])
    return correct / len(test_x)


def run_method(method, seed, budget, initial_k=5):
    """One (method, seed) active-learning run; returns the learning curve."""
    if method not in METHODS:
        raise ValueError('unknown method %r' % (method,))
    bundle = build(seed=seed)
    oracle = bundle['oracle']
    pool = bundle['pool']
    test_x = test_features(seed)                    # evaluation only
    test_labels = oracle.reveal(sorted(test_x))     # reveal for the scorer
    pool_ids = {it['id'] for it in pool.items()}
    if pool_ids & set(test_x):
        raise AssertionError('pool/test id overlap')

    store = AnnotationStore(budget=Budget(budget))
    remaining = pool.items()                        # label-free {id, x}
    labeled = []                                    # pool-only {id, x, y}
    curve = []
    touched_test = []                               # ids selection ever saw

    def _score():
        curve.append({'labels_acquired': store.acquired_count,
                      'test_accuracy': round(_accuracy(labeled, test_x,
                                                       test_labels), 6)})

    init_ids = _initial_ids(pool.items(), seed, initial_k)
    revealed = oracle.reveal(init_ids)
    for iid in init_ids:
        idx = next(i for i, r in enumerate(remaining) if r['id'] == iid)
        item = remaining.pop(idx)
        store.label(iid, revealed[iid], 'oracle')
        labeled.append({'id': iid, 'x': item['x'], 'y': revealed[iid]})
        _score()

    sel_rng = random.Random(seed + 2)
    while store.acquired_count < budget and remaining:
        # Selection sees only the label-free remaining pool + pool-only labeled.
        for r in remaining:
            touched_test.append(r['id'] in test_x)
        i = select(remaining, labeled, method, sel_rng)
        item = remaining.pop(i)
        if item['id'] in test_x:
            raise AssertionError('selector touched a test id')
        y = oracle.reveal([item['id']])[item['id']]
        store.label(item['id'], y, 'oracle')
        labeled.append({'id': item['id'], 'x': item['x'], 'y': y})
        _score()

    finals = [c['test_accuracy'] for c in curve]
    return {'method': method, 'seed': seed, 'budget': budget,
            'initial_ids': init_ids, 'acquired': store.acquired_count,
            'curve': curve, 'final_accuracy': finals[-1] if finals else 0.0,
            'selection_saw_test_id': any(touched_test),
            'pool_sha256': bundle['pool_sha256'],
            'test_sha256': bundle['test_sha256']}


def run_experiment(seeds=(0, 1, 2), budget=40, initial_k=5, methods=METHODS):
    """Matched-budget, matched-seed comparison across all methods."""
    runs = [run_method(m, s, budget, initial_k)
            for s in seeds for m in methods]
    return {'seeds': list(seeds), 'budget': budget, 'initial_k': initial_k,
            'methods': list(methods), 'runs': runs}


def average_curve(experiment, method):
    """Seed-averaged (labels_acquired -> mean accuracy) for one method."""
    curves = [r['curve'] for r in experiment['runs'] if r['method'] == method]
    if not curves:
        return []
    length = min(len(c) for c in curves)
    out = []
    for i in range(length):
        accs = [c[i]['test_accuracy'] for c in curves]
        out.append({'labels_acquired': curves[0][i]['labels_acquired'],
                    'mean_accuracy': round(sum(accs) / len(accs), 6),
                    'n_seeds': len(accs)})
    return out


def _mean_std(values):
    n = len(values)
    if n == 0:
        return 0.0, 0.0
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / n
    return mean, var ** 0.5


def summarize(experiment):
    summary = {}
    for method in experiment['methods']:
        finals = [r['final_accuracy'] for r in experiment['runs']
                  if r['method'] == method]
        mean, std = _mean_std(finals)
        summary[method] = {'final_accuracy_mean': round(mean, 6),
                           'final_accuracy_std': round(std, 6),
                           'per_seed_final': [round(f, 6) for f in finals],
                           'n_seeds': len(finals)}
    return summary


def curves_to_csv(experiment):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(['method', 'seed', 'labels_acquired', 'test_accuracy'])
    for run in experiment['runs']:
        for point in run['curve']:
            writer.writerow([run['method'], run['seed'],
                             point['labels_acquired'], point['test_accuracy']])
    return buf.getvalue()


def render_svg(experiment, width=640, height=400):
    """Dependency-free SVG line chart of the seed-averaged learning curves."""
    left, right, top, bottom = 60, 20, 30, 50
    plot_w = width - left - right
    plot_h = height - top - bottom
    series = {m: average_curve(experiment, m) for m in experiment['methods']}
    max_x = max((p['labels_acquired'] for c in series.values() for p in c),
                default=1)
    min_y, max_y = 0.4, 1.0

    def sx(x):
        return left + (x / max_x) * plot_w if max_x else left

    def sy(y):
        clamped = max(min_y, min(max_y, y))
        return top + (1 - (clamped - min_y) / (max_y - min_y)) * plot_h

    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
             'viewBox="0 0 %d %d" font-family="monospace" font-size="12">'
             % (width, height, width, height)]
    parts.append('<rect width="%d" height="%d" fill="white"/>'
                 % (width, height))
    parts.append('<text x="%d" y="18" text-anchor="middle" font-size="14">'
                 'P10-03 held-out learning curves (mean over %d seeds)</text>'
                 % (width // 2, len(experiment['seeds'])))
    # axes + y gridlines
    for gy in (0.4, 0.55, 0.7, 0.85, 1.0):
        yy = sy(gy)
        parts.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" '
                     'stroke="#eee"/>' % (left, yy, left + plot_w, yy))
        parts.append('<text x="%d" y="%.1f" text-anchor="end" fill="#555">'
                     '%.2f</text>' % (left - 6, yy + 4, gy))
    parts.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#333"/>'
                 % (left, top, left, top + plot_h))
    parts.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#333"/>'
                 % (left, top + plot_h, left + plot_w, top + plot_h))
    parts.append('<text x="%d" y="%d" text-anchor="middle" fill="#333">'
                 'labels acquired</text>' % (left + plot_w // 2, height - 12))
    # x ticks
    for gx in range(0, max_x + 1, max(1, max_x // 5)):
        parts.append('<text x="%.1f" y="%d" text-anchor="middle" fill="#555">'
                     '%d</text>' % (sx(gx), top + plot_h + 16, gx))
    # series
    legend_y = top + 6
    for method in experiment['methods']:
        curve = series[method]
        if not curve:
            continue
        pts = ' '.join('%.1f,%.1f' % (sx(p['labels_acquired']),
                                      sy(p['mean_accuracy'])) for p in curve)
        color = _COLORS.get(method, '#000')
        parts.append('<polyline fill="none" stroke="%s" stroke-width="2" '
                     'points="%s"/>' % (color, pts))
        parts.append('<rect x="%d" y="%d" width="10" height="10" fill="%s"/>'
                     % (left + plot_w - 120, legend_y - 9, color))
        parts.append('<text x="%d" y="%d" fill="#333">%s</text>'
                     % (left + plot_w - 106, legend_y, method))
        legend_y += 16
    parts.append('</svg>')
    return '\n'.join(parts)


def source_hash():
    """sha256 over the modules that define this experiment."""
    import experiment
    import pool
    import project
    h = hashlib.sha256()
    for mod in (pool, project, experiment):
        with open(mod.__file__, 'rb') as handle:
            h.update(handle.read())
    return h.hexdigest()
