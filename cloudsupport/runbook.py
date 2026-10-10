"""Run all support cases, write results/casebook.json. Exit 1 on any failure (skips ok)."""
import json
import sys

sys.path.insert(0, "src")
from cases import CASES

results = []
for name, fn in CASES.items():
    try:
        rec = fn()
    except Exception as e:  # noqa: BLE001 — record, don't crash the runbook
        rec = {"name": name, "outcome": "error", "steps": [],
               "note": f"{type(e).__name__}: {e}"}
    results.append(rec)
    print(f"{rec['name']}: {rec['outcome']}")

with open("results/casebook.json", "w") as fh:
    json.dump(results, fh, indent=2)

failed = [r["name"] for r in results if r["outcome"] not in ("pass", "skip")]
sys.exit(1 if failed else 0)
