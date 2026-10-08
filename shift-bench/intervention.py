"""One-intervention comparison for ShiftBench (P09-04 shared core).

Intervention: noise-augmented centroids — fit class centroids on train
plus one gaussian-noise copy (sigma 1.5, seed 1000+split_seed) of each
train image. Ablation grid is 2x2: augmentation {off,on} x temperature
{1.0, validation-chosen}. Everything reuses P09-01 splits and P09-03
corruptions; test is scored once per cell. Returns per-seed tables plus
averages so the write-up and its tests share one code path.
"""
import numpy as np

from baseline import fit_centroids, predict_logits
from corrupt import CORRUPTIONS, SEEDS, apply
from dataset import load_dataset
from project import choose_temperature, metrics
from splits import entity_split


def _rows_for(parts, pack, index, labels, name):
    return [(pack['images'][index[sample]], labels[index[sample]], sample)
            for sample in parts[name]]


def run_intervention(split_seed, augment_sigma=1.5):
    """2x2 ablation for one split seed; returns conditions + temperature."""
    pack = load_dataset()
    parts = entity_split(pack['sample_ids'], pack['entity_ids'],
                         seed=split_seed)
    index = {sample: pos
             for pos, sample in enumerate(pack['sample_ids'])}
    labels = [int(value) for value in pack['labels']]
    train_rows = _rows_for(parts, pack, index, labels, 'train')
    val_rows = _rows_for(parts, pack, index, labels, 'validation')
    test_rows = _rows_for(parts, pack, index, labels, 'test')
    train_images = np.stack([image for image, _, _ in train_rows])
    train_labels = [label for _, label, _ in train_rows]

    base_centroids = fit_centroids(train_images, train_labels)
    rng = np.random.RandomState(1000 + split_seed)
    noisy = (train_images.astype(np.float64)
             + rng.normal(0, augment_sigma, size=train_images.shape))
    doubled = np.concatenate([train_images.astype(np.float64), noisy])
    doubled_labels = train_labels + train_labels
    aug_centroids = fit_centroids(doubled.astype(np.float32),
                                 doubled_labels)

    def kernel_for(rows, centroids, images=None):
        stacked = images if images is not None else np.stack(
            [image for image, _, _ in rows])
        logits = predict_logits(stacked, centroids)
        return [{'id': sample, 'logits': logit, 'label': label}
                for (_, label, sample), logit in zip(rows, logits)]

    val_kernel = kernel_for(val_rows, base_centroids)
    temperature = choose_temperature(val_kernel)
    test_images = np.stack([image for image, _, _ in test_rows])
    conditions = {}
    for label, centroids in (('baseline', base_centroids),
                             ('augmented', aug_centroids)):
        for suffix, temp in (('raw', 1.0), ('calibrated', temperature)):
            key = '%s+%s' % (label, suffix)
            kernel = kernel_for(test_rows, centroids, test_images)
            conditions[key] = metrics(kernel, temperature=temp)
            for spec in CORRUPTIONS:
                shifted = apply(test_images, spec, seed=split_seed)
                cell = kernel_for(test_rows, centroids, shifted)
                conditions['%s+%s+%s' % (label, suffix,
                                         spec['name'])] = metrics(
                                             cell, temperature=temp)
    return {'temperature': temperature, 'conditions': conditions,
            'augment_sigma': augment_sigma}


def average_over_seeds():
    """Mean test accuracy per ablation cell across SEEDS (original only)."""
    cells = {}
    for seed in SEEDS:
        run = run_intervention(seed)
        for key in ('baseline+raw', 'baseline+calibrated',
                    'augmented+raw', 'augmented+calibrated'):
            cells.setdefault(key, []).append(
                run['conditions'][key]['accuracy'])
    return {key: sum(values) / len(values) for key, values in cells.items()}
