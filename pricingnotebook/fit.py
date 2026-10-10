"""Fit frequency + severity models, out-of-time test, calibration, bootstrap lift."""
import json
import sys

import numpy as np

sys.path.insert(0, "src")
from glm import COLS, design, ols, poisson_deviance, poisson_irls

SEED = 42
rows = np.genfromtxt("datasets/policies.csv", delimiter=",", names=True)
with open("datasets/truth.json") as _fh:
    truth = json.load(_fh)
tr = np.isin(rows["period"], truth["train_periods"])
te = ~tr

Xtr, Xte = design(rows[tr]), design(rows[te])
ytr, yte = rows["claims"][tr].astype(float), rows["claims"][te].astype(float)
otr, ote = np.log(rows["exposure"][tr]), np.log(rows["exposure"][te])

beta, se, info = poisson_irls(Xtr, ytr, otr)
mu_te = np.exp(Xte @ beta + ote)
b0 = np.log(ytr.sum() / np.exp(otr).sum())
mu_base = np.exp(b0 + ote)
dev_model = poisson_deviance(yte, mu_te)
dev_base = poisson_deviance(yte, mu_base)

rng = np.random.default_rng(SEED)
lifts = []
n = len(yte)
for _ in range(500):
    idx = rng.integers(0, n, n)
    lifts.append(poisson_deviance(yte[idx], mu_base[idx]) - poisson_deviance(yte[idx], mu_te[idx]))
lifts.sort()

# calibration deciles on test
order = np.argsort(mu_te)
dec = np.array_split(order, 10)
calib = [{"pred": round(float(mu_te[d].mean()), 4), "actual": round(float(yte[d].mean()), 4)}
         for d in dec]

# severity: OLS on log mean severity, rows with claims (train only)
mtr = ytr > 0
sev_beta, sev_se = ols(Xtr[mtr], np.log(rows["paid"][tr][mtr] / ytr[mtr]))

out = {
    "freq_beta": {c: round(float(b), 4) for c, b in zip(COLS, beta)},
    "freq_se": {c: round(float(s), 4) for c, s in zip(COLS, se)},
    "freq_truth": truth["B_FREQ"],
    "test_deviance": {"model": round(dev_model, 2), "baseline": round(dev_base, 2),
                      "lift": round(dev_base - dev_model, 2),
                      "lift_ci95": [round(lifts[12], 2), round(lifts[487], 2)]},
    "calibration_deciles": calib,
    "sev_beta": {c: round(float(b), 4) for c, b in zip(COLS, sev_beta)},
    "sev_se": {c: round(float(s), 4) for c, s in zip(COLS, sev_se)},
    "sev_truth": truth["B_SEV"],
    "n_train": int(tr.sum()), "n_test": int(te.sum()),
    "irls": info,
}
json.dump(out, open("results/fit.json", "w"), indent=2)
print(json.dumps({k: v for k, v in out.items() if k != "calibration_deciles"}, indent=2))
