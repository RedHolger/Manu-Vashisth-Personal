# PartnerOps

Partner-pipeline reporting with explicit definitions for win rate, deal size and enablement completion. PostgreSQL queries calculate the metrics; Python produces a JSON report and a short narrative using the same numbers.

The fixture includes duplicates, missing amounts, unknown stages and an outlier. Tests compare the results with hand calculations, including which deals belong in each denominator.

## Run against a disposable database

Use PostgreSQL 16 and Python 3 with `psycopg` installed. Create an empty test database, then set its connection string:

```bash
export PARTNEROPS_DSN='dbname=partnerops host=127.0.0.1 port=55434'
python3 -m unittest discover -s tests -v
python3 kpi.py
```

The tests prepare fixture tables; use a database reserved for this project. Reports are written to `results/kpis.json` and `results/report.html`.

`pg.sh` automates a local cluster on port 55434, but contains the author's virtual-environment path. Adapt that path before using the helper on another machine.

The SQL is in `sql/`. [SPEC.md](SPEC.md) contains the KPI definitions and [PROVENANCE.md](PROVENANCE.md) explains the synthetic data. The results do not describe an actual partner programme.
