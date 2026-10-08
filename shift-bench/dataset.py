"""CC0 synthetic vision dataset for ShiftBench (P09-01 stand-in).

No network is available in this workspace, so no external vision set can
be downloaded and pinned here. This module generates a tiny openly
licensed (CC0-1.0, public domain dedication) 8x8 pattern dataset with
explicit entity structure — 30 entities x 10 images — so the split
protocol, hashing and leakage checks run on real files before any licensed
external set arrives. It is synthetic and nonclinical; never present it
as clinical evidence. The selected external candidate is documented in
DATA_SOURCE.md (MedMNIST BloodMNIST, CC BY) with its exact fetch command.
"""
import hashlib
import json
from pathlib import Path

import numpy as np

LICENSE = 'CC0-1.0'
N_ENTITIES = 30
IMAGES_PER_ENTITY = 10
IMAGE_SHAPE = (8, 8)
SEED = 7

HERE = Path(__file__).parent
DATA_DIR = HERE / 'data'


def generate(seed=SEED, n_entities=N_ENTITIES,
             per_entity=IMAGES_PER_ENTITY):
    """Deterministic patterns: class = (entity_index + image_index) % 2.

    Class 0 draws a horizontal bar, class 1 a vertical bar, plus seeded
    Gaussian noise. Entity ids look like person-00; sample ids like
    person-00-img-03. Returns (images, labels, entity_ids, sample_ids).
    """
    rng = np.random.RandomState(seed)
    images, labels, entities, samples = [], [], [], []
    for entity in range(n_entities):
        entity_id = 'person-%02d' % entity
        for image in range(per_entity):
            label = (entity + image) % 2
            canvas = np.zeros(IMAGE_SHAPE, dtype=np.float64)
            if label == 0:
                canvas[3:5, :] = 1.0
            else:
                canvas[:, 3:5] = 1.0
            canvas += rng.normal(0, 0.2, size=IMAGE_SHAPE)
            images.append(canvas.astype(np.float32))
            labels.append(label)
            entities.append(entity_id)
            samples.append('%s-img-%02d' % (entity_id, image))
    return (np.stack(images), np.array(labels, dtype=np.int64),
            entities, samples)


def save_dataset(directory=None, seed=SEED):
    """Write npz + license + manifest; returns the manifest dict."""
    out = Path(directory) if directory else DATA_DIR
    out.mkdir(parents=True, exist_ok=True)
    images, labels, entities, samples = generate(seed=seed)
    npz_path = out / 'synthetic_cc0.npz'
    np.savez_compressed(npz_path, images=images, labels=labels,
                        entity_ids=np.array(entities),
                        sample_ids=np.array(samples))
    (out / 'LICENSE_CC0.txt').write_text(
        'CC0 1.0 Universal (public domain dedication).\n'
        'This synthetic dataset was generated locally by dataset.py;\n'
        'no rights reserved. Not clinical data.\n', encoding='utf-8')
    digest = hashlib.sha256(npz_path.read_bytes()).hexdigest()
    manifest = {
        'name': 'synthetic-cc0-8x8-patterns',
        'license': LICENSE,
        'access': 'generated locally by dataset.py; no download required',
        'seed': seed,
        'n_entities': N_ENTITIES,
        'images_per_entity': IMAGES_PER_ENTITY,
        'n_images': len(samples),
        'image_shape': list(IMAGE_SHAPE),
        'file': npz_path.name,
        'sha256': digest,
        'bytes': npz_path.stat().st_size,
    }
    (out / 'manifest.json').write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + '\n',
        encoding='utf-8')
    return manifest


def load_dataset(directory=None):
    """Load the saved npz; returns dict of arrays + id lists."""
    out = Path(directory) if directory else DATA_DIR
    pack = np.load(out / 'synthetic_cc0.npz', allow_pickle=False)
    return {'images': pack['images'], 'labels': pack['labels'],
            'entity_ids': [str(value) for value in pack['entity_ids']],
            'sample_ids': [str(value) for value in pack['sample_ids']]}
