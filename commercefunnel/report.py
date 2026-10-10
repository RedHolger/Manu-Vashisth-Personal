"""Build the fixture store, compute funnel, write report.json + report.html."""
import json
import sys

sys.path.insert(0, "src")
from funnel import cohorts, funnel, ingest, init_db, ontime_rate, substitution_rate

with open("datasets/events.json") as fh:
    rows = [tuple(r) for r in json.load(fh)]
db = init_db()
dups = ingest(db, rows)
rep = {
    "events": len(rows),
    "deduped": dups,
    "funnel": funnel(db),
    "substitution": substitution_rate(db),
    "ontime": ontime_rate(db),
    "cohorts": cohorts(db),
    "primary": "view_purchase",
    "guardrails": ["substitution", "ontime"],
    "experiment": "PROPOSED ONLY (see experiment.md) — not run, no results",
}
json.dump(rep, open("results/report.json", "w"), indent=2)
def cell(v):
    if v["frac"] is None:
        return f"n/a ({v['unavailable']})"
    return str(v["frac"])


rows_html = "".join(
    f"<tr><td>{k}</td><td>{v['rate']}</td><td>{cell(v)}</td><td>{v['ci95']}</td></tr>"
    for k, v in rep["funnel"].items())
coh = "".join(
    f"<tr><td>{k}</td><td>{v['rate']}</td></tr>" for k, v in rep["cohorts"].items())
open("results/report.html", "w").write(
    f"<!doctype html><html><body><h1>CommerceFunnel — snapshot</h1>"
    f"<p>Events {rep['events']}, exact replays deduped {rep['deduped']}. "
    f"Substitution {rep['substitution']['rate']}, on-time {rep['ontime']['rate']}.</p>"
    f"<h2>Funnel (distinct users, Wilson 95%)</h2>"
    f"<table border='1'><tr><th>step</th><th>rate</th><th>frac</th><th>ci</th></tr>{rows_html}</table>"
    f"<h2>Cohorts (purchase rate)</h2><table border='1'>{coh}</table>"
    f"<p>Primary metric: view_purchase. Guardrails: substitution, on-time. "
    f"Experiment proposal only — no uplift claimed. Synthetic data.</p></body></html>")
print(json.dumps({k: v for k, v in rep.items()}, indent=2)[:600])
