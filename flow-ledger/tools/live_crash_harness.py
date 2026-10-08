#!/usr/bin/env python3
"""Live crash-boundary harness for P04-03.

Runs the packaged FlowLedger application as REAL OS processes against the
persistent PostgreSQL container, injects crashes at the two named boundaries by
halting the JVM at a precise point, restarts the process, and asserts the
recovery invariants against the database.

Scenarios
  S1 effect-before-ack        worker dies after the downstream effect commits and
                              before the local completion transaction
  S2 stale-generation fencing two live workers; the first one resumes after its
                              lease was taken over by a higher generation
  S3 consumer-before-dispatch relay dies after the consumer accepted the event
                              and before outbox_events.dispatched is set

Fault hooks are configuration-gated and default off:
  --flowledger.fault.halt-after-effect=true
  --flowledger.fault.sleep-after-effect-ms=<ms>
  --flowledger.fault.halt-after-consumer-accept=true

Usage:  python3 tools/live_crash_harness.py
Exit:   0 when every assertion holds, 1 otherwise.
"""
import datetime
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JAR = os.path.join(ROOT, "target", "flowledger-0.1.0.jar")
RESULTS = os.path.join(ROOT, "results", "p04-03-live-crash")
CONTAINER = "p04-flowledger-postgres-1"
PORT_A = 18084
PORT_B = 18085

ASSERTIONS = []          # (scenario, label, ok, detail)
LOGS = {}                # scenario -> open file handle
PROC_SEQ = [0]           # each launched process gets its own log file


def log(scenario, line):
    handle = LOGS.get(scenario)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S.%f")[:-3]
    text = f"{stamp} {line}"
    if handle:
        handle.write(text + "\n")
        handle.flush()
    print(text, flush=True)


def check(scenario, label, ok, detail=""):
    ASSERTIONS.append((scenario, label, bool(ok), detail))
    log(scenario, f"{'PASS' if ok else 'FAIL'}: {label}" + (f" | {detail}" if detail else ""))
    return bool(ok)


def sql(query):
    r = subprocess.run(
        ["docker", "exec", CONTAINER, "psql", "-U", "flowledger", "-d", "flowledger",
         "-tA", "-v", "ON_ERROR_STOP=1", "-c", query],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"sql failed: {query}\n{r.stderr}")
    return r.stdout.strip()


def scalar(query):
    out = sql(query)
    return out.splitlines()[0] if out else ""


def reset_db():
    sql("TRUNCATE attempts, results, outbox_events, downstream_effects, consumer_seen, jobs CASCADE;")
    log("setup", "database truncated for scenario")


def http(port, method, path, body=None, headers=None):
    url = f"http://127.0.0.1:{port}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw or "{}")
        except json.JSONDecodeError:
            return e.code, {"raw": raw}


def wait_ready(port, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            status, body = http(port, "GET", "/health")
            if status == 200 and body.get("status") == "OK":
                return True
        except OSError:
            pass
        time.sleep(0.25)
    return False


def wait_for(predicate, timeout, interval=0.25):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


def wait_status(port, job_id, status, timeout=60):
    def probe():
        try:
            s, body = http(port, "GET", f"/jobs/{job_id}")
            return s == 200 and body.get("status") == status
        except OSError:
            return False
    return wait_for(probe, timeout)


def submit(port, key):
    status, body = http(port, "POST", "/jobs",
                        body={"type": "echo", "payload": {"scenario": key}},
                        headers={"Idempotency-Key": key})
    if status not in (200, 201):
        raise RuntimeError(f"submit failed: {status} {body}")
    return body["jobId"]


def start(scenario, port, extra_args):
    os.makedirs(RESULTS, exist_ok=True)
    PROC_SEQ[0] += 1
    log_path = os.path.join(RESULTS, f"{scenario}-app{port}-p{PROC_SEQ[0]}.log")
    args = ["java", "-jar", JAR, f"--server.port={port}"] + list(extra_args)
    log(scenario, f"start: {' '.join(args)}")
    log(scenario, f"      stdout -> {os.path.basename(log_path)}")
    handle = open(log_path, "w")
    proc = subprocess.Popen(args, stdout=handle, stderr=subprocess.STDOUT, cwd=ROOT)
    return proc, handle, log_path


def stop(scenario, proc, handle, expect_code=None, timeout=90):
    code = None
    if expect_code is None:
        # Caller just wants the process gone (it should already have halted or
        # is still running cleanly) — do not wait for a natural exit.
        if proc.poll() is None:
            proc.terminate()
        try:
            code = proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            code = proc.wait(timeout=15)
    else:
        try:
            code = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:
                code = proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
                code = proc.wait(timeout=15)
    handle.close()
    if expect_code is not None:
        check(scenario, f"process exit code == {expect_code}", code == expect_code, f"actual {code}")
    else:
        log(scenario, f"process stopped with code {code}")
    return code


def grep_log(path, needle, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with open(path) as fh:
                if needle in fh.read():
                    return True
        except OSError:
            pass
        time.sleep(0.25)
    return False


def attempt_rows(job_id):
    return sql(
        "SELECT generation || ':' || outcome FROM attempts WHERE job_id='{}' "
        "ORDER BY generation".format(job_id))


# --------------------------------------------------------------------------
def scenario_effect_before_ack():
    sc = "S1-effect-before-ack"
    LOGS[sc] = open(os.path.join(RESULTS, f"{sc}.log"), "w")
    log(sc, "=== S1: process dies between downstream effect commit and local completion ===")
    reset_db()

    proc, handle, log_path = start(sc, PORT_A, [
        "--flowledger.worker.leaseMillis=2000",
        "--flowledger.fault.halt-after-effect=true",
    ])
    try:
        check(sc, "app became healthy", wait_ready(PORT_A, 60))
        job_id = submit(PORT_A, "p04-03-s1")
        log(sc, f"submitted job {job_id}")

        code = stop(sc, proc, handle, expect_code=77, timeout=60)
        log(sc, f"crashed process exit code {code}")

        check(sc, "downstream effect survived the crash (count == 1)",
              scalar(f"SELECT count(*) FROM downstream_effects WHERE job_id='{job_id}'") == "1")
        check(sc, "job not completed by the crashed process (status == LEASED)",
              scalar(f"SELECT status FROM jobs WHERE id='{job_id}'") == "LEASED")
        check(sc, "no result row written (count == 0)",
              scalar(f"SELECT count(*) FROM results WHERE job_id='{job_id}'") == "0")
        check(sc, "no outbox event written (count == 0)",
              scalar(f"SELECT count(*) FROM outbox_events WHERE job_id='{job_id}'") == "0")
        check(sc, "attempt 1 left STARTED by the crash, generation 1",
              attempt_rows(job_id) == "1:STARTED", attempt_rows(job_id))

        log(sc, "restarting a fresh process with no fault injection")
        proc2, handle2, log_path2 = start(sc, PORT_A, ["--flowledger.worker.leaseMillis=2000"])
        try:
            check(sc, "recovered process became healthy", wait_ready(PORT_A, 60))
            check(sc, "job reached SUCCEEDED after recovery",
                  wait_status(PORT_A, job_id, "SUCCEEDED", 60))
            check(sc, "lease generation advanced to 2 (higher generation took over)",
                  scalar(f"SELECT lease_generation FROM jobs WHERE id='{job_id}'") == "2")
            check(sc, "exactly one logical downstream side effect (count == 1)",
                  scalar(f"SELECT count(*) FROM downstream_effects WHERE job_id='{job_id}'") == "1")
            check(sc, "attempt trail is closed: gen1 ABANDONED, gen2 SUCCEEDED",
                  attempt_rows(job_id) == "1:ABANDONED\n2:SUCCEEDED", attempt_rows(job_id))
            check(sc, "exactly one result row",
                  scalar(f"SELECT count(*) FROM results WHERE job_id='{job_id}'") == "1")

            # The relay runs on its own 500ms schedule; wait for it rather than
            # asserting a race against the poller.
            check(sc, "exactly one outbox event dispatched",
                  wait_for(lambda: scalar(
                      f"SELECT count(*) FROM outbox_events WHERE job_id='{job_id}' AND dispatched=TRUE") == "1", 30))
            check(sc, "exactly one consumer effect",
                  scalar("SELECT count(*) FROM consumer_seen") == "1",
                  scalar("SELECT count(*) FROM consumer_seen"))
        finally:
            stop(sc, proc2, handle2)
    finally:
        if sc in LOGS:
            LOGS[sc].close()
            del LOGS[sc]


def scenario_stale_generation_fencing():
    sc = "S2-stale-generation-fencing"
    LOGS[sc] = open(os.path.join(RESULTS, f"{sc}.log"), "w")
    log(sc, "=== S2: two live workers; the loser resumes with an expired generation ===")
    reset_db()

    proc_a, handle_a, log_path_a = start(sc, PORT_A, [
        "--flowledger.worker.leaseMillis=3000",
        "--flowledger.fault.sleep-after-effect-ms=12000",
    ])
    try:
        check(sc, "worker A became healthy", wait_ready(PORT_A, 60))
        job_id = submit(PORT_A, "p04-03-s2")
        log(sc, f"submitted job {job_id}")

        check(sc, "worker A leased generation 1",
              wait_for(lambda: scalar(f"SELECT lease_generation FROM jobs WHERE id='{job_id}'") == "1", 20))
        check(sc, "worker A committed the downstream effect",
              wait_for(lambda: scalar(f"SELECT count(*) FROM downstream_effects WHERE job_id='{job_id}'") == "1", 20))

        proc_b, handle_b, log_path_b = start(sc, PORT_B, ["--flowledger.worker.leaseMillis=3000"])
        try:
            check(sc, "worker B became healthy", wait_ready(PORT_B, 60))
            check(sc, "worker B took over with generation 2 after A's lease expired",
                  wait_for(lambda: scalar(f"SELECT lease_generation FROM jobs WHERE id='{job_id}'") == "2", 30))
            check(sc, "worker B completed the job",
                  wait_status(PORT_B, job_id, "SUCCEEDED", 60))

            check(sc, "stale worker A was fenced out (log contains 'stale commit rejected')",
                  grep_log(log_path_a, "stale commit rejected", 40))
            check(sc, "job still SUCCEEDED after A's stale commit attempt",
                  scalar(f"SELECT status FROM jobs WHERE id='{job_id}'") == "SUCCEEDED")
            check(sc, "lease generation still 2 (stale commit did not advance it)",
                  scalar(f"SELECT lease_generation FROM jobs WHERE id='{job_id}'") == "2")
            check(sc, "result belongs to generation 2",
                  scalar(f"SELECT count(*) FROM results WHERE job_id='{job_id}'") == "1")
            check(sc, "attempt trail: gen1 ABANDONED, gen2 SUCCEEDED",
                  attempt_rows(job_id) == "1:ABANDONED\n2:SUCCEEDED", attempt_rows(job_id))
            check(sc, "exactly one logical downstream side effect despite two workers",
                  scalar(f"SELECT count(*) FROM downstream_effects WHERE job_id='{job_id}'") == "1")
            check(sc, "exactly one outbox event dispatched",
                  scalar(f"SELECT count(*) FROM outbox_events WHERE job_id='{job_id}' AND dispatched=TRUE") == "1")
            check(sc, "exactly one consumer effect",
                  scalar("SELECT count(*) FROM consumer_seen") == "1")
        finally:
            stop(sc, proc_b, handle_b)
    finally:
        stop(sc, proc_a, handle_a)
        if sc in LOGS:
            LOGS[sc].close()
            del LOGS[sc]


def scenario_consumer_before_dispatch():
    sc = "S3-consumer-before-dispatch"
    LOGS[sc] = open(os.path.join(RESULTS, f"{sc}.log"), "w")
    log(sc, "=== S3: process dies between consumer acceptance and outbox dispatched mark ===")
    reset_db()

    proc, handle, log_path = start(sc, PORT_A, [
        "--flowledger.fault.halt-after-consumer-accept=true",
    ])
    try:
        check(sc, "app became healthy", wait_ready(PORT_A, 60))
        job_id = submit(PORT_A, "p04-03-s3")
        log(sc, f"submitted job {job_id}")

        check(sc, "job reached SUCCEEDED before the relay crash",
              wait_status(PORT_A, job_id, "SUCCEEDED", 60))
        code = stop(sc, proc, handle, expect_code=77, timeout=60)
        log(sc, f"crashed process exit code {code}")

        check(sc, "consumer accepted the event (count == 1)",
              scalar("SELECT count(*) FROM consumer_seen") == "1")
        check(sc, "outbox event NOT yet marked dispatched",
              scalar(f"SELECT dispatched FROM outbox_events WHERE job_id='{job_id}'") == "f",
              scalar(f"SELECT dispatched FROM outbox_events WHERE job_id='{job_id}'"))
        check(sc, "job result already durable",
              scalar(f"SELECT count(*) FROM results WHERE job_id='{job_id}'") == "1")

        log(sc, "restarting a fresh process with no fault injection")
        proc2, handle2, log_path2 = start(sc, PORT_A, [])
        try:
            check(sc, "recovered process became healthy", wait_ready(PORT_A, 60))
            check(sc, "outbox event now dispatched",
                  wait_for(lambda: scalar(
                      f"SELECT dispatched FROM outbox_events WHERE job_id='{job_id}'") == "t", 45),
                  scalar(f"SELECT dispatched FROM outbox_events WHERE job_id='{job_id}'"))
            check(sc, "consumer effect NOT duplicated by the replay (count == 1)",
                  scalar("SELECT count(*) FROM consumer_seen") == "1",
                  scalar("SELECT count(*) FROM consumer_seen"))
            check(sc, "job still SUCCEEDED", scalar(f"SELECT status FROM jobs WHERE id='{job_id}'") == "SUCCEEDED")
            check(sc, "downstream side effect still exactly one",
                  scalar(f"SELECT count(*) FROM downstream_effects WHERE job_id='{job_id}'") == "1")
        finally:
            stop(sc, proc2, handle2)
    finally:
        if sc in LOGS:
            LOGS[sc].close()
            del LOGS[sc]


def write_environment():
    def run(cmd):
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return (r.stdout + r.stderr).strip()
    template = "{{.Config.Image}} {{.State.Status}}"
    pg = run("docker inspect -f '" + template + "' " + CONTAINER)
    lines = [
        f"captured_at_utc: {datetime.datetime.now(datetime.timezone.utc).isoformat()}",
        f"host: {socket.gethostname()}",
        f"platform: {sys.platform}",
        f"python: {sys.version.split()[0]}",
        f"java: {run('java -version 2>&1 | head -1')}",
        f"maven: {run('mvn -v | head -1')}",
        f"jar: {JAR} ({os.path.getsize(JAR) if os.path.exists(JAR) else 'MISSING'} bytes)",
        f"postgres: {pg}",
        f"ports: A={PORT_A} B={PORT_B}",
    ]
    with open(os.path.join(RESULTS, "environment.txt"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    return "\n".join(lines)


def write_summary():
    passed = sum(1 for a in ASSERTIONS if a[2])
    failed = len(ASSERTIONS) - passed
    with open(os.path.join(RESULTS, "assertions.txt"), "w") as fh:
        for scenario, label, ok, detail in ASSERTIONS:
            fh.write(f"{'PASS' if ok else 'FAIL'}\t{scenario}\t{label}\t{detail}\n")
    summary = {
        "run_id": "p04-03-live-crash",
        "captured_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scenarios": ["S1 effect-before-ack", "S2 stale-generation fencing",
                      "S3 consumer-before-dispatch"],
        "assertions_total": len(ASSERTIONS),
        "assertions_passed": passed,
        "assertions_failed": failed,
        "failed": [f"{s}: {l}" for s, l, ok, _ in ASSERTIONS if not ok],
    }
    with open(os.path.join(RESULTS, "summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2)
        fh.write("\n")
    return summary, passed, failed


def main():
    if not os.path.exists(JAR):
        print(f"jar not found: {JAR}  (run: mvn -q package -DskipTests)", file=sys.stderr)
        return 2
    if os.path.exists(RESULTS):
        shutil.rmtree(RESULTS)
    os.makedirs(RESULTS, exist_ok=True)

    print(write_environment())
    print()

    scenario_effect_before_ack()
    scenario_stale_generation_fencing()
    scenario_consumer_before_dispatch()

    summary, passed, failed = write_summary()
    print()
    print(f"assertions: {passed} passed, {failed} failed, {len(ASSERTIONS)} total")
    if summary["failed"]:
        for f in summary["failed"]:
            print(f"  FAIL {f}")
    with open(os.path.join(RESULTS, "exit-status.txt"), "w") as fh:
        fh.write(f"assertions_passed={passed}\nassertions_failed={failed}\nexit={0 if failed == 0 else 1}\n")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
