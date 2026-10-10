#!/bin/bash
# Local PostgreSQL 16 lifecycle for ReadingQueue tests. No Docker needed.
# Usage: ./pg.sh   (initdb once, start, createdb, mvn test, stop)
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
DATA="$HERE/.pgdata"
PORT=55433
export PATH="/opt/homebrew/bin:$PATH"
if [ ! -d "$DATA" ]; then
  initdb -D "$DATA" -E UTF8 > /dev/null
fi
pg_ctl -D "$DATA" -o "-p $PORT -k /tmp" -l "$HERE/.pg.log" start
trap 'pg_ctl -D "$DATA" stop' EXIT
psql -h 127.0.0.1 -p $PORT -d postgres -tc "SELECT 1 FROM pg_database WHERE datname='readingqueue'" | grep -q 1 \
  || psql -h 127.0.0.1 -p $PORT -d postgres -c "CREATE DATABASE readingqueue"
cd "$HERE/backend" && mvn -q test -DjdbcUrl="jdbc:postgresql://127.0.0.1:$PORT/readingqueue" -Dmigrations="$HERE/db/postgres"
