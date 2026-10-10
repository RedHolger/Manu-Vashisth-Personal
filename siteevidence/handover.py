"""Static handover pack: JSON + HTML snapshot of all RFIs/inspections/gaps."""
import html
import json
import sys

sys.path.insert(0, "backend")
import store

db = store.init_db()
from store import handover  # noqa: E402

pack = handover(db)
json.dump(pack, open("results/handover.json", "w"), indent=2)
rrows = "".join(
    f"<tr><td>{r['id']}</td><td>{html.escape(r['title'])}</td><td>{r['owner']}</td>"
    f"<td>{r['due']}</td><td>{r['status']}</td><td>{r['rev']}</td></tr>" for r in pack["rfis"])
irows = "".join(
    f"<tr><td>{r['id']}</td><td>{r['rfi']}</td><td>{r['rev']}</td><td>{r['date']}</td>"
    f"<td>{r['result']}</td><td>{html.escape(str(r['evidence']))}</td></tr>" for r in pack["inspections"])
g = pack["gaps"]
open("results/handover.html", "w").write(
    f"<!doctype html><html><body><h1>SiteEvidence handover pack (as of {g.get('as_of', '')})</h1>"
    f"<table border='1'><tr><th>RFI</th><th>title</th><th>owner</th><th>due</th>"
    f"<th>status</th><th>rev</th></tr>{rrows}</table>"
    f"<table border='1'><tr><th>inspection</th><th>rfi</th><th>rev</th><th>date</th>"
    f"<th>result</th><th>evidence</th></tr>{irows}</table>"
    f"<p>Overdue: {g['overdue']}; missing evidence: {g['missing_evidence']}; "
    f"mismatches: {g['mismatches']}; failed: {g['failed']}.</p>"
    f"<p>{html.escape(pack['note'])}</p></body></html>")
print(f"handover: {len(pack['rfis'])} rfis, {len(pack['inspections'])} inspections, "
      f"overdue={g['overdue']}")
