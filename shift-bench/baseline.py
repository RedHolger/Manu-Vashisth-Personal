"""Manageable CPU baseline for ShiftBench (P09-02): nearest-centroid.

Fits class centroids on the TRAIN entities only, scores every sample by
negative squared distance to each centroid (raw logits, no calibration),
and evaluates with the reference kernel's metrics(). The checkpoint
(centroids + config + dependency versions) plus the dataset/split
manifests reproduce the logits byte-identically. No torch, no clinical
claim; temperature scaling and corruptions are P09-03 work.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

from dataset import DATA_DIR, load_dataset
from project import metrics
from splits import entity_split, write_split_manifest

HERE = Path(__file__).parent
CHECKPOINT_DIR = HERE / 'checkpoints'


def versions():
    """Pinned runtime identity for the checkpoint."""
    import platform
    return {'python': platform.python_version(),
            'numpy': np.__version__,
            'platform': platform.platform()}


def fit_centroids(images, labels):
    """Class centroids for labels 0/1; raises on degenerate input."""
    classes = sorted(set(int(value) for value in labels))
    if classes != [0, 1]:
        raise ValueError('baseline needs exactly classes {0,1}')
    flat = images.reshape(len(images), -1).astype(np.float64)
    return {label: flat[np.asarray(labels) == label].mean(axis=0)
            for label in classes}


def predict_logits(images, centroids):
    """Negative squared distances as 2-logits, ordered [class0, class1]."""
    flat = images.reshape(len(images), -1).astype(np.float64)
    stacked = np.stack([centroids[0], centroids[1]])
    dists = ((flat[:, None, :] - stacked[None, :, :]) ** 2).sum(axis=2)
    return (-dists).tolist()


def train_and_evaluate(split_seed=0, dataset_seed=7):
    """Fit on train, evaluate on val/test; returns report + artifacts."""
    from dataset import save_dataset
    dataset_manifest = save_dataset(seed=dataset_seed)
    pack = load_dataset()
    parts = entity_split(pack['sample_ids'], pack['entity_ids'],
                         seed=split_seed)
    index = {sample: position
             for position, sample in enumerate(pack['sample_ids'])}
    images = pack['images']
    labels = [int(value) for value in pack['labels']]
    partition_rows = {}
    for name, ids in parts.items():
        rows = []
        for sample in ids:
            position = index[sample]
            rows.append({'id': sample,
                         'image': images[position],
                         'label': labels[position]})
        partition_rows[name] = rows
    train_images = np.stack([row['image'] for row in partition_rows['train']])
    train_labels = [row['label'] for row in partition_rows['train']]
    centroids = fit_centroids(train_images, train_labels)
    logits_by_part = {}
    metrics_by_part = {}
    for name, rows in partition_rows.items():
        stacked = np.stack([row['image'] for row in rows])
        logits = predict_logits(stacked, centroids)
        logits_by_part[name] = logits
        kernel_rows = [{'id': row['id'], 'logits': logit,
                        'label': row['label']}
                       for row, logit in zip(rows, logits)]
        metrics_by_part[name] = metrics(kernel_rows)
    checkpoint = {'centroid_0': centroids[0], 'centroid_1': centroids[1],
                  'split_seed': split_seed, 'dataset_seed': dataset_seed,
                  'dataset_sha256': dataset_manifest['sha256'],
                  'versions': versions()}
    return {'dataset_manifest': dataset_manifest, 'parts': parts,
            'logits': logits_by_part, 'metrics': metrics_by_part,
            'checkpoint': checkpoint,
            'labels': {name: [row['label'] for row in rows]
                       for name, rows in partition_rows.items()},
            'ids': {name: [row['id'] for row in rows]
                    for name, rows in partition_rows.items()}}


def save_checkpoint(checkpoint, directory=None):
    """Freeze centroids + config; returns (npz_path, manifest)."""
    out = Path(directory) if directory else CHECKPOINT_DIR
    out.mkdir(parents=True, exist_ok=True)
    npz_path = out / 'baseline-centroids.npz'
    np.savez_compressed(npz_path, centroid_0=checkpoint['centroid_0'],
                        centroid_1=checkpoint['centroid_1'])
    manifest = {'split_seed': checkpoint['split_seed'],
                'dataset_seed': checkpoint['dataset_seed'],
                'dataset_sha256': checkpoint['dataset_sha256'],
                'versions': checkpoint['versions'],
                'centroid_sha256': hashlib.sha256(
                    npz_path.read_bytes()).hexdigest()}
    (out / 'baseline-manifest.json').write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    return npz_path, manifest


def load_checkpoint(directory=None):
    """Reload centroids + manifest."""
    out = Path(directory) if directory else CHECKPOINT_DIR
    pack = np.load(out / 'baseline-centroids.npz', allow_pickle=False)
    manifest = json.loads((out / 'baseline-manifest.json').read_text())
    return ({0: pack['centroid_0'], 1: pack['centroid_1']}, manifest)


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', help='write logits/metrics/manifests here')
    parser.add_argument('--split-seed', type=int, default=0)
    options = parser.parse_args(argv)
    report = train_and_evaluate(split_seed=options.split_seed)
    npz_path, manifest = save_checkpoint(report['checkpoint'])
    summary = {
        'test': report['metrics']['test'],
        'validation': report['metrics']['validation'],
        'checkpoint': str(npz_path.name),
        'versions': report['checkpoint']['versions'],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    if options.out:
        out = Path(options.out)
        out.mkdir(parents=True, exist_ok=True)
        for name, logits in report['logits'].items():
            np.save(out / ('logits-%s.npy' % name), np.asarray(logits))
        (out / 'metrics.json').write_text(
            json.dumps(report['metrics'], indent=2, sort_keys=True) + '\n')
        (out / 'baseline-manifest.copy.json').write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
