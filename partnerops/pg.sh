#!/bin/bash
# Local PostgreSQL lifecycle for PartnerOps tests + KPI run.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
DATA="$HERE/.pgdata-po"
PORT=55434
export PATH="/opt/homebrew/bin:$PATH"
export PARTNEROPS_DSN="dbname=partnerops host=127.0.0.1 port=$PORT"
[ -d "$DATA" ] || initdb -D "$DATA" -E UTF8 > /dev/null
pg_ctl -D "$DATA" -o "-p $PORT -k /tmp" -l "$HERE/.pg.log" start > /dev/null
trap 'pg_ctl -D "$DATA" stop > /dev/null 2>&1' EXIT
psql -h 127.0.0.1 -p $PORT -d postgres -tc "SELECT 1 FROM pg_database WHERE datname='partnerops'" | grep -q 1 \
  || psql -h 127.0.0.1 -p $PORT -d postgres -c "CREATE DATABASE partnerops" > /dev/null
VENV=/Users/manuvashistha/Developer/MANU_INTERNSHIP_OPPURTUNITIES/.venv-builds/bin/python
cd "$HERE" && $VENV -m unittest discover -s tests -v && $VENV kpi.py
