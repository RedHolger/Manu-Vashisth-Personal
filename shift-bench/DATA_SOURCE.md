# Data source — P09 ShiftBench (P09-01)

- Stand-in dataset (vendored): `data/synthetic_cc0.npz` — 300 8x8 patterns,
  30 entities x 10 images, CC0-1.0 public-domain dedication generated locally
  by `dataset.py` (seed 7). Manifest: `data/manifest.json` (sha256, counts,
  seed). License text: `data/LICENSE_CC0.txt`. Access: no download.
- This stand-in is **synthetic and nonclinical**. It exercises the entity
  split, hashing and leakage checks; it is not a vision benchmark and makes
  no clinical claim.
- Selected external candidate (not yet fetched — no network in this
  workspace): **MedMNIST BloodMNIST** (28x28 blood-cell images, CC BY 4.0,
  11,959 train / 1,712 val / 3,421 test as published). Intended fetch:

```sh
pip install medmnist==0.2.2
python3 -B -c "from medmnist import BloodMNIST; d=BloodMNIST(split='train', download=True, root='./data/bloodmnist')"
```

  On a networked machine, record the downloaded file sha256, the package
  version and the published split counts in `data/external-manifest.json`
  before replacing the stand-in. Until then P09-02..04 run on the CC0
  stand-in and say so.
- Split protocol: `splits.py` — entities ordered by `sha256(seed:entity)`,
  60/20/20 entities to train/validation/test; manifests hash the sorted id
  lists. Overlap or duplicate ids raise via the reference `validate_splits`.
- Privacy: entity ids (`person-NN`) are fictitious. Retention: generated
  arrays live under `data/` (git-tracked, no personal data). No patient,
  video or clinical data is present.
