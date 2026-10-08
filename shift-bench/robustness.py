"""Validation-only calibration + shifted evaluation (P09-03 shared core)."""
import numpy as np

from baseline import fit_centroids, predict_logits
from corrupt import CORRUPTIONS, apply
from dataset import load_dataset
from project import choose_temperature, metrics
from splits import entity_split


def run_seed(split_seed):
    """Fit on train, pick temperature on validation, score test shifts."""
    pack = load_dataset()
    parts = entity_split(pack['sample_ids'], pack['entity_ids'],
                         seed=split_seed)
    index = {sample: pos
             for pos, sample in enumerate(pack['sample_ids'])}
    images = pack['images']
    labels = [int(value) for value in pack['labels']]
    by_part = {}
    for name, ids in parts.items():
        rows = [(images[index[sample]], labels[index[sample]], sample)
                for sample in ids]
        by_part[name] = rows
    train_images = np.stack([image for image, _, _ in by_part['train']])
    train_labels = [label for _, label, _ in by_part['train']]
    centroids = fit_centroids(train_images, train_labels)

    def score(rows, images_override=None):
        stacked = (images_override if images_override is not None
                   else np.stack([image for image, _, _ in rows]))
        logits = predict_logits(stacked, centroids)
        kernel = [{'id': sample, 'logits': logit, 'label': label}
                  for (_, label, sample), logit in zip(rows, logits)]
        return logits, kernel

    _, val_kernel = score(by_part['validation'])
    temperature = choose_temperature(val_kernel)
    val_before = metrics(val_kernel, temperature=1.0)
    val_after = metrics(val_kernel, temperature=temperature)

    test_images = np.stack([image for image, _, _ in by_part['test']])
    _, test_kernel = score(by_part['test'], test_images)
    result = {'temperature': temperature,
              'validation_before': val_before, 'validation_after': val_after,
              'conditions': {'original': metrics(test_kernel),
                             'original_calibrated': metrics(
                                 test_kernel, temperature=temperature)},
              'per_group_original': _per_group(by_part['test'],
                                              test_kernel)}
    for spec in CORRUPTIONS:
        shifted = apply(test_images, spec, seed=split_seed)
        _, kernel = score(by_part['test'], shifted)
        result['conditions'][spec['name']] = metrics(kernel)
        result['conditions'][spec['name'] + '+calibrated'] = metrics(
            kernel, temperature=temperature)
    return result


def _per_group(rows, kernel):
    """Accuracy/NLL denominators per class label on one condition."""
    groups = {}
    for (_, label, _), entry in zip(rows, kernel):
        groups.setdefault(label, []).append(entry)
    out = {}
    for label, entries in sorted(groups.items()):
        wrapped = [{'id': str(index), 'logits': item['logits'],
                    'label': item['label']}
                   for index, item in enumerate(entries)]
        measured = metrics(wrapped)
        out['label-%d' % label] = {'n': measured['n'],
                                  'accuracy': measured['accuracy'],
                                  'nll': measured['nll']}
    return out
