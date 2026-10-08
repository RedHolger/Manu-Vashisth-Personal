"""Entity-aware split protocol for ShiftBench (P09-01).

Splits by entity (person/video), never by sample, so no entity appears in
two partitions. Entity order is fixed by sha256(seed + entity_id); the
first 60% of entities go to train, next 20% to validation, rest to test.
Split IDs are hashed into the manifest (sha256 of the sorted id list) so
a later run can prove it used the same partition. Validation reuses the
reference kernel's validate_splits() on {id, group} rows.
"""
import hashlib
import json
from pathlib import Path

from project import validate_splits

RATIOS = (0.6, 0.2, 0.2)


def _entity_order(entity_ids, seed):
    keyed = sorted(
        set(entity_ids),
        key=lambda entity: hashlib.sha256(
            ('%d:%s' % (seed, entity)).encode()).hexdigest())
    return keyed


def entity_split(sample_ids, entity_ids, seed=0, ratios=RATIOS):
    """Split sample ids by entity; returns {train, validation, test}."""
    if len(sample_ids) != len(entity_ids):
        raise ValueError('samples and entities must align')
    if not sample_ids:
        raise ValueError('no samples to split')
    if abs(sum(ratios) - 1.0) > 1e-9 or any(value <= 0 for value in ratios):
        raise ValueError('ratios must be positive and sum to 1')
    ordered = _entity_order(entity_ids, seed)
    total = len(ordered)
    train_end = int(total * ratios[0])
    val_end = train_end + int(total * ratios[1])
    groups = {'train': set(ordered[:train_end]),
              'validation': set(ordered[train_end:val_end]),
              'test': set(ordered[val_end:])}
    if not all(groups.values()):
        raise ValueError('split left a partition empty; add entities')
    parts = {'train': [], 'validation': [], 'test': []}
    entity_of = dict(zip(sample_ids, entity_ids))
    for sample in sample_ids:
        entity = entity_of[sample]
        for name, members in groups.items():
            if entity in members:
                parts[name].append(sample)
                break
    # Reference leakage check on {id, group} rows.
    rows = {name: [{'id': sample,
                    'group': entity_of[sample]} for sample in ids]
            for name, ids in parts.items()}
    validate_splits(rows['train'], rows['validation'], rows['test'])
    return parts


def _hash_ids(ids):
    return hashlib.sha256(
        '\n'.join(sorted(ids)).encode()).hexdigest()


def write_split_manifest(sample_ids, entity_ids, seed, out_path):
    """Split, hash and freeze the manifest; returns it."""
    parts = entity_split(sample_ids, entity_ids, seed)
    entity_of = dict(zip(sample_ids, entity_ids))
    manifest = {
        'seed': seed,
        'ratios': list(RATIOS),
        'rule': 'split by entity, order by sha256(seed:entity)',
        'partitions': {},
    }
    for name, ids in parts.items():
        entities = sorted({entity_of[sample] for sample in ids})
        manifest['partitions'][name] = {
            'n_samples': len(ids),
            'n_entities': len(entities),
            'entities': entities,
            'sample_sha256': _hash_ids(ids),
            'entity_sha256': _hash_ids(entities),
        }
    out = Path(out_path)
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n',
                   encoding='utf-8')
    return manifest
