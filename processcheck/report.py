"""Batch-quality report: charts verdicts + capability + actions -> JSON + HTML."""
import html
import json
import sys

sys.path.insert(0, "src")
from charts import capability, limits, load_batches, verdicts

stats = load_batches("datasets/batches.csv")
lim = limits(stats)
ver = verdicts(stats, lim)
cap = capability(stats)
actions = json.load(open("datasets/actions.json"))
rep = {
    "limits": {k: round(v, 4) for k, v in lim.items()},
    "verdicts": ver,
    "capability": cap,
    "actions": actions,
    "note": "Fictional print limits 9.55-10.45; normality assumed untested. "
            "No GMP or regulatory validation.",
}
json.dump(rep, open("results/report.json", "w"), indent=2)
rows = "".join(
    f"<tr><td>{b}</td><td>{stats[b]['mean'] and round(stats[b]['mean'], 4)}</td>"
    f"<td>{round(stats[b]['rng'], 4) if stats[b]['rng'] is not None else '—'}</td>"
    f"<td>{', '.join(ver[b]) or 'in control'}</td><td>{stats[b]['nulls']}</td></tr>"
    for b in sorted(stats))
arows = "".join(
    f"<tr><td>{a['batch']}</td><td>{html.escape(a['cause'])}</td>"
    f"<td>{html.escape(a['action'])}</td><td>{a['status']}</td></tr>" for a in actions)
open("results/report.html", "w").write(
    "<!doctype html><html><body><h1>ProcessCheck — batch quality</h1>"
    f"<p>X-bar limits [{lim['xbar_lcl']:.4f}, {lim['xbar_ucl']:.4f}]; "
    f"Cp {cap['cp']}, Cpk {cap['cpk']} (normality assumed, untested).</p>"
    "<table border='1'><tr><th>batch</th><th>mean</th><th>range</th><th>verdict</th>"
    f"<th>nulls</th></tr>{rows}</table>"
    f"<h2>Corrective actions</h2><table border='1'>{arows}</table>"
    "<p>Teaching fixture. No GMP or medical-device regulatory validation.</p></body></html>")
print(f"flagged={[b for b, v in ver.items() if v]}, cpk={cap['cpk']}")
