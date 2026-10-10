"""Synthetic seal-width batches (seed 3). Writes datasets/batches.csv."""
import csv

import numpy as np

SEED, N = 3, 20
rng = np.random.default_rng(SEED)
rows = []
for b in range(1, 11):
    mean = 10.0 + (0.35 if b in (7, 8) else 0.0)
    vals = rng.normal(mean, 0.1, N)
    if b == 9:
        vals[rng.choice(N, 3, replace=False)] = np.nan
    for i, v in enumerate(vals):
        rows.append([f"B{b:02d}", i + 1, "" if np.isnan(v) else round(float(v), 4)])

with open("datasets/batches.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["batch", "unit", "width_mm"])
    w.writerows(rows)
print(f"batches=10 n={N} nulls={sum(1 for r in rows if r[2] == '')}")
