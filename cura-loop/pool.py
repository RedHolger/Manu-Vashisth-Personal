"""Pool/label separation for CuraLoop (P10-01): selection never sees labels.

Entities (30 groups x 5 points in 2D, seed-fixed) are ordered by
sha256(seed:entity) exactly like the P09 split discipline; the first 20
entities form the pool, the last 10 the held-out test. Labels live in
exactly one place — Oracle — and reach selection only through
oracle.reveal(id), which appends to a query log. PoolView items carry
{id, x} and no 'y'; select_* functions accept (pool_view, labeled, rng)
where labeled items are {id, x, y} for already-queried ids only. Test
labels are never attached to any object selection can touch.
"""
import hashlib
import random

N_ENTITIES = 30
POINTS_PER_ENTITY = 5
POOL_ENTITIES = 20


def _generate(seed=7):
    rng = random.Random(seed)
    rows = []
    for entity in range(N_ENTITIES):
        entity_id = 'entity-%02d' % entity
        for point in range(POINTS_PER_ENTITY):
            x = [rng.uniform(-1, 1), rng.uniform(-1, 1)]
            rows.append({'id': '%s-p%d' % (entity_id, point),
                         'entity': entity_id, 'x': x,
                         'y': int(sum(x) > 0)})
    return rows


def _entity_order(rows, seed):
    entities = sorted({row['entity'] for row in rows},
                      key=lambda entity: hashlib.sha256(
                          ('%d:%s' % (seed, entity)).encode()).hexdigest())
    return entities


class Oracle:
    """Hidden labels; every reveal is logged."""

    def __init__(self, rows):
        self._labels = {row['id']: row['y'] for row in rows}
        self.queries = []

    def reveal(self, ids):
        """Return {id: label} for the requested ids; log them."""
        unique = list(dict.fromkeys(ids))
        unknown = [ident for ident in unique if ident not in self._labels]
        if unknown:
            raise ValueError('unknown ids %r' % (unknown,))
        self.queries.extend(unique)
        return {ident: self._labels[ident] for ident in unique}

    def queried(self):
        """Ids revealed so far (copy)."""
        return list(self.queries)


class PoolView:
    """Label-free pool; items expose {id, x} only."""

    def __init__(self, rows):
        self._items = [{'id': row['id'], 'x': list(row['x'])}
                       for row in rows]

    def __len__(self):
        return len(self._items)

    def items(self):
        """Shallow copies without labels."""
        return [dict(item) for item in self._items]

    def pop(self, index):
        """Remove and return the item at index (label-free)."""
        return self._items.pop(index)


def test_features(seed=7):
    """Evaluation-only ``{id: x}`` for the held-out test rows.

    Added for P10-03 so the experimenter can score held-out accuracy. These
    features must never be handed to a selector; labels stay in the Oracle
    and are revealed only on the evaluation path. Selection keeps using the
    label-free PoolView.
    """
    rows = _generate(seed=seed)
    ordered = _entity_order(rows, seed)
    pool_entities = set(ordered[:POOL_ENTITIES])
    return {row['id']: list(row['x']) for row in rows
            if row['entity'] not in pool_entities}


def build(seed=7):
    """Entity-split pool/test + oracle; returns dict of parts."""
    rows = _generate(seed=seed)
    ordered = _entity_order(rows, seed)
    pool_entities = set(ordered[:POOL_ENTITIES])
    pool_rows = [row for row in rows if row['entity'] in pool_entities]
    test_rows = [row for row in rows if row['entity'] not in pool_entities]
    assert not ({row['entity'] for row in pool_rows}
                & {row['entity'] for row in test_rows})
    oracle = Oracle(pool_rows + test_rows)
    pool_ids = sorted(row['id'] for row in pool_rows)
    test_ids = sorted(row['id'] for row in test_rows)
    return {
        'seed': seed,
        'pool': PoolView(pool_rows),
        'test_ids': test_ids,
        'test_entities': sorted({row['entity'] for row in test_rows}),
        'pool_entities': sorted({row['entity'] for row in pool_rows}),
        'pool_sha256': hashlib.sha256(
            '\n'.join(pool_ids).encode()).hexdigest(),
        'test_sha256': hashlib.sha256(
            '\n'.join(test_ids).encode()).hexdigest(),
        'oracle': oracle,
        'n_pool': len(pool_ids),
        'n_test': len(test_ids),
    }
