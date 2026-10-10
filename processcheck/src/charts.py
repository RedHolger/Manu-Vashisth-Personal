"""X-bar/R charts, capability, validation. numpy only.

SPC constants for subgroup n=20 (standard tables): d2=3.735 → A2=0.1796;
d3=0.729 → D3=0.4145, D4=1.5855. Rule 1 only (point beyond limits).
"""
import math

N = 20
A2, D3, D4 = 0.1796, 0.4145, 1.5855
LO, HI = 8.0, 12.0  # physical plausibility gate (mm)
LSL, USL = 9.55, 10.45  # fictional print limits (NOT a device master record)
BASELINE = [f"B{b:02d}" for b in range(1, 6)]


def batch_stats(values):
    """values: list of floats/None. Returns dict with null/range accounting."""
    nulls = sum(1 for v in values if v is None)
    bad = sum(1 for v in values if v is not None and not (LO <= v <= HI))
    good = [v for v in values if v is not None and LO <= v <= HI]
    if not good:
        return {"n": len(values), "nulls": nulls, "quarantined": bad,
                "mean": None, "rng": None}
    return {"n": len(values), "nulls": nulls, "quarantined": bad,
            "mean": sum(good) / len(good), "rng": max(good) - min(good)}


def limits(stats):
    """Control limits from BASELINE batches."""
    base = [stats[b] for b in BASELINE]
    xbar = sum(s["mean"] for s in base) / len(base)
    rbar = sum(s["rng"] for s in base) / len(base)
    return {"xbar_c": xbar, "xbar_ucl": xbar + A2 * rbar, "xbar_lcl": xbar - A2 * rbar,
            "r_ucl": D4 * rbar, "r_lcl": D3 * rbar, "rbar": rbar}


def verdicts(stats, lim):
    out = {}
    for b, s in stats.items():
        flags = []
        if s["mean"] is None:
            flags.append("no-valid-readings")
        else:
            if s["mean"] > lim["xbar_ucl"] or s["mean"] < lim["xbar_lcl"]:
                flags.append("xbar-beyond-limits")
            if s["rng"] > lim["r_ucl"] or s["rng"] < lim["r_lcl"]:
                flags.append("r-beyond-limits")
        out[b] = flags
    return out


def capability(stats):
    """Cp/Cpk on BASELINE valid readings vs spec limits. Normality ASSUMED
    (no test performed — documented openly)."""
    import statistics
    vals = []
    for b in BASELINE:
        vals.extend(stats[b].get("values", []))
    mu = sum(vals) / len(vals)
    sd = statistics.pstdev(vals)
    cp = (USL - LSL) / (6 * sd)
    cpk = min(USL - mu, mu - LSL) / (3 * sd)
    return {"cp": round(cp, 3), "cpk": round(cpk, 3), "n": len(vals),
            "normality": "assumed, untested"}


def load_batches(path):
    import csv
    stats, order = {}, []
    with open(path) as fh:
        for row in list(csv.DictReader(fh)):
            b = row["batch"]
            if b not in stats:
                stats[b] = {"vals": []}
                order.append(b)
            stats[b]["vals"].append(float(row["width_mm"]) if row["width_mm"] else None)
    out = {}
    for b in order:
        s = batch_stats(stats[b]["vals"])
        s["values"] = [v for v in stats[b]["vals"] if v is not None and LO <= v <= HI]
        out[b] = s
    return out
