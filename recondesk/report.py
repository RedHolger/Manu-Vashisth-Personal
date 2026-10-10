"""Build the fixture ledger, reconcile, write results/report.json + report.html."""
import html
import json
import sys

sys.path.insert(0, "src")
from ledger import init_db, reconcile, report, seed

fx = json.load(open("datasets/fixtures.json"))
db = init_db()
seed(db, [tuple(r) for r in fx["invoices"]], [tuple(r) for r in fx["payments"]])
rep = report(db, reconcile(db))
json.dump(rep, open("results/report.json", "w"), indent=2)

rows = "".join(
    f"<tr><td>{html.escape(r['invoice'])}</td><td>{html.escape(r['status'])}</td>"
    f"<td>{r['open_base']}</td><td>{html.escape(r['bucket'])}</td>"
    f"<td>{r['past_due_days']}</td></tr>" for r in rep["open_rows"])
exc = "".join(
    f"<tr><td>{html.escape(e['kind'])}</td><td>{html.escape(e.get('payment', ''))}</td>"
    f"<td>{html.escape(str(e.get('ref', '')))}</td></tr>" for e in rep["exceptions"])
open("results/report.html", "w").write(f"""<!doctype html><html><body>
<h1>ReconciliationDesk — working-capital snapshot (as of {rep['as_of']})</h1>
<p><b>Definitions:</b> {html.escape(rep['definitions'])}</p>
<p>Match rate {rep['match_rate']}; invoiced {rep['invoiced_base_minor']} minor (EUR base);
open {rep['open_base_minor']} minor.</p>
<h2>Open items</h2><table border="1"><tr><th>invoice</th><th>status</th>
<th>open (minor, EUR base)</th><th>bucket</th><th>past-due days</th></tr>{rows}</table>
<h2>Exceptions</h2><table border="1"><tr><th>kind</th><th>payment</th><th>ref</th></tr>{exc}</table>
<p>Educational snapshot. No financial advice; no bank-system connection.</p>
</body></html>""")
print(f"match {rep['match_rate']}, open_base={rep['open_base_minor']}, "
      f"exceptions={len(rep['exceptions'])}")
