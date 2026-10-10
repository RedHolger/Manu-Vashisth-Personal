#!/bin/bash
# End-to-end demo: local PG + Java backend + Python API transcript.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
PORT=55433
API=8581
export PATH="/opt/homebrew/bin:$PATH"
[ -d "$HERE/.pgdata" ] || initdb -D "$HERE/.pgdata" -E UTF8 > /dev/null
pg_ctl -D "$HERE/.pgdata" -o "-p $PORT -k /tmp" -l "$HERE/.pg.log" start > /dev/null
trap 'pg_ctl -D "$HERE/.pgdata" stop > /dev/null 2>&1' EXIT
psql -h 127.0.0.1 -p $PORT -d postgres -tc "SELECT 1 FROM pg_database WHERE datname='readingqueue'" | grep -q 1 \
  || psql -h 127.0.0.1 -p $PORT -d postgres -c "CREATE DATABASE readingqueue" > /dev/null
cd "$HERE/backend" && mvn -q compile > /dev/null 2>&1
CP=$(mvn -q dependency:build-classpath -Dmdep.outputFile=/dev/stdout 2>/dev/null | tail -n 1)
JDBC_URL="jdbc:postgresql://127.0.0.1:$PORT/readingqueue" \
  java -cp "target/classes:$CP" queue.Server $API > /tmp/rq_demo_srv.log 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null; pg_ctl -D "$HERE/.pgdata" stop > /dev/null 2>&1' EXIT
for i in $(seq 1 50); do
  curl -s -o /dev/null "http://127.0.0.1:$API/api/items" && break
  sleep 0.2
done
cd "$HERE" && python3 demo_api.py $API
