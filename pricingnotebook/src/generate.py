"""Synthetic policy-month data with known truth (seed 5). Writes datasets/policies.csv."""
import csv

import numpy as np

SEED = 5
rng = np.random.default_rng(SEED)
N_POL, N_PER = 800, 10
B_FREQ = {"intercept": -2.0, "young": 0.6, "urban": 0.5, "suv": 0.3}
B_SEV = {"intercept": 6.5, "suv": 0.2, "urban": 0.1}
SIGMA = 0.4

rows = []
for p in range(N_POL):
    young = int(rng.random() < 0.3)
    urban = int(rng.random() < 0.5)
    suv = int(rng.random() < 0.4)
    lam = np.exp(B_FREQ["intercept"] + B_FREQ["young"] * young
                 + B_FREQ["urban"] * urban + B_FREQ["suv"] * suv)
    mu = B_SEV["intercept"] + B_SEV["suv"] * suv + B_SEV["urban"] * urban
    for t in range(1, N_PER + 1):
        expo = 0.5 + 0.5 * rng.random()
        n = rng.poisson(lam * expo)
        paid = float(np.sum(rng.lognormal(mu, SIGMA, size=n))) if n else 0.0
        rows.append([f"P{p:04d}", t, young, urban, suv, round(expo, 4), n, round(paid, 2)])

with open("datasets/policies.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["policy", "period", "young", "urban", "suv", "exposure", "claims", "paid"])
    w.writerows(rows)

truth = {"B_FREQ": B_FREQ, "B_SEV": B_SEV, "SIGMA": SIGMA, "seed": SEED,
         "train_periods": [1, 2, 3, 4, 5, 6, 7], "test_periods": [8, 9, 10]}
import json
json.dump(truth, open("datasets/truth.json", "w"), indent=1)
print(f"rows={len(rows)} claims={sum(r[6] for r in rows)}")
