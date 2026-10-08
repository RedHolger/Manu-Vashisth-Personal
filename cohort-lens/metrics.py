"""SQL metric runner for CohortLens (P08-01): the same cohorts as SQL.

`sql_cohorts` runs metrics.sql against an ingest.py store and returns the
cohort table in exactly the shape of `project.cohorts()['cohorts']`, so the
contract test can demand equality instead of eyeballing two reports.
"""
from pathlib import Path

from ingest import parse_utc

QUERY = Path(__file__).with_name('metrics.sql').read_text(encoding='utf-8')


def sql_cohorts(conn, asof):
    """Cohort table from SQL; cutoff normalized to stored UTC form."""
    cutoff = parse_utc(asof).isoformat()
    groups = {}
    for monday, users, activated, eligible, retained, retention in \
            conn.execute(QUERY, {'asof': cutoff}).fetchall():
        groups[monday] = {'users': users, 'activated': activated,
                          'week1_eligible': eligible,
                          'week1_retained': retained,
                          'week1_retention': retention}
    return groups
