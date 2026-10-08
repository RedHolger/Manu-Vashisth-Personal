"""Shared database helpers for the P05 test and measurement modules.

Not named `test_*` so unittest discovery does not try to collect it.
"""
import os
from contextlib import contextmanager

import psycopg

from pg_store import DEFAULT_DSN, PgStore, migrate

DSN = os.environ.get('P05_DATABASE_URL', DEFAULT_DSN)

TOKEN_ALPHA = 'local-demo-alpha-token'
TOKEN_BETA = 'local-demo-beta-token'
USER_ALPHA, TENANT_ALPHA = 'alice', 'alpha'
USER_BETA, TENANT_BETA = 'bob', 'beta'

DOC_ALPHA = 'refund-policy'
DOC_BETA = 'invoice-nightfall'
TEXT_ALPHA = 'Refunds take five working days. Support is open Monday to Friday.'
TEXT_BETA = ('Beta invoice total is 999 credits. '
             'Marker BETA-SECRET-9f3a must never leak.')
MARKERS_ALPHA = ('five working days', DOC_ALPHA)
MARKERS_BETA = ('BETA-SECRET-9f3a', '999 credits', DOC_BETA)
# Every string that must never appear in the *other* tenant's responses.
SECRET_MARKERS = MARKERS_ALPHA + MARKERS_BETA

RECORD_ALPHA = 'limits'
RECORD_BETA = 'invoice'
VALUE_ALPHA = {'daily': 100, 'plan': 'standard'}
VALUE_BETA = {'total': 999, 'project': 'NIGHTFALL'}

TABLES = ('retrieval_cache', 'tenant_generation', 'chunks',
          'document_versions', 'query_runs', 'grants', 'documents',
          'records', 'sessions')


def database_available(timeout=3):
    try:
        with psycopg.connect(DSN, connect_timeout=timeout) as conn:
            conn.execute('SELECT 1')
        return True
    except Exception:
        return False


def reset_tables(conn):
    # One statement: PostgreSQL refuses to truncate a table that another table
    # references by foreign key unless both are named together.
    with conn.transaction():
        conn.execute('TRUNCATE %s' % ', '.join(TABLES))


def seed_tenants(store):
    """Two isolated tenants, each with one document and one structured record."""
    store.session(TOKEN_ALPHA, USER_ALPHA, TENANT_ALPHA)
    store.session(TOKEN_BETA, USER_BETA, TENANT_BETA)
    store.put(TOKEN_ALPHA, DOC_ALPHA, TEXT_ALPHA)
    store.put(TOKEN_BETA, DOC_BETA, TEXT_BETA)
    store.put_record(TENANT_ALPHA, RECORD_ALPHA, VALUE_ALPHA)
    store.put_record(TENANT_BETA, RECORD_BETA, VALUE_BETA)


@contextmanager
def fresh_store(dsn=DSN, seed=True):
    """A migrated store with empty tables, seeded with the two-tenant fixture."""
    store = PgStore(dsn, run_migrations=False)
    try:
        migrate(store.conn)
        reset_tables(store.conn)
        if seed:
            seed_tenants(store)
        yield store
    finally:
        store.close()
