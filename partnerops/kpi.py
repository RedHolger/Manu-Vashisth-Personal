"""PartnerOps KPIs: run canonical SQL, narrative + static dashboard."""
import json
import os
import statistics
import sys

import psycopg

DSN = os.environ.get("PARTNEROPS_DSN", "dbname=partnerops host=127.0.0.1 port=55434")


def load_queries():
    parts, cur = {}, []
    name = None
    with open("sql/queries.sql") as fh:
        lines = fh.readlines()
    for line in lines:
        if line.startswith("-- name: "):
            if name:
                parts[name] = "".join(cur)
            name, cur = line[len("-- name: "):].strip(), []
        else:
            cur.append(line)
    if name:
        parts[name] = "".join(cur)
    return parts


def compute():
    q = load_queries()
    with psycopg.connect(DSN) as db:
        won, lost = db.execute(q["win_rate"]).fetchone()
        amounts = [r[0] for r in db.execute(q["won_amounts"]).fetchall()]
        med = statistics.median(amounts)
        outliers = [a for a in amounts if a > 3 * med]
        base = [a for a in amounts if a <= 3 * med]
        avg = round(sum(base) / len(base), 2)
        dup = db.execute(q["duplicates"]).fetchone()[0]
        missing = db.execute(q["missing_amount"]).fetchone()[0]
        unknown = [r[0] for r in db.execute(q["unknown_stage"]).fetchall()]
        done, total = db.execute(q["enablement"]).fetchone()
    return {
        "win_rate": f"{won}/{won + lost}",
        "win_rate_pct": round(100 * won / (won + lost), 2),
        "avg_won_size": avg,
        "avg_basis": f"{len(base)} deals",
        "outliers": {"count": len(outliers), "median": med, "rule": "> 3x median"},
        "missing_amount": missing,
        "unknown_stage": unknown,
        "duplicates": dup,
        "enablement": f"{done}/{total}",
        "enablement_pct": round(100 * done / total, 2),
    }


def narrative(k):
    return (
        f"Partner pipeline: win rate {k['win_rate']} ({k['win_rate_pct']}%), average won "
        f"deal EUR {k['avg_won_size']} over {k['avg_basis']}; {k['outliers']['count']} outlier "
        f"excluded by the 3x-median rule; {k['missing_amount']} rows lack amounts, "
        f"{len(k['unknown_stage'])} lack a stage, {k['duplicates']} duplicate ext_id deduped. "
        f"Enablement completion {k['enablement']} ({k['enablement_pct']}%). "
        "Every excluded row is counted above; open pipeline is outside win-rate scope.")


def main():
    k = compute()
    k["narrative"] = narrative(k)
    json.dump(k, open("results/kpis.json", "w"), indent=2)
    li = "".join(f"<li>{kk}: {vv}</li>" for kk, vv in k.items() if kk != "narrative")
    open("results/report.html", "w").write(
        f"<!doctype html><html><body><h1>PartnerOps — executive snapshot</h1>"
        f"<p>{k['narrative']}</p><ul>{li}</ul>"
        f"<h2>Data dictionary</h2><p>partners(id, name, tier, region); "
        f"deals(ext_id, partner_id, stage won/lost/open/NULL, amount_eur NULL-able, created); "
        f"enablement(partner_id, module, done). Rules: win=won/(won+lost); avg over won "
        f"non-null non-outlier; outlier &gt; 3x median; NULL stage = unknown bucket; "
        f"duplicates deduped keeping earliest id.</p>"
        f"<p>Synthetic data. No SAP system involved.</p></body></html>")
    print(k["narrative"])
    return k


if __name__ == "__main__":
    main()
