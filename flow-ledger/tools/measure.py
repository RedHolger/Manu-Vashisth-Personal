#!/usr/bin/env python3
"""P04-04 measurement: steady-state load with identical producer schedules.

Runs the packaged FlowLedger application against persistent PostgreSQL and drives
one fixed producer schedule per run, twice:

  baseline  fault-free steady-state load
  fault     the SAME schedule, with the process SIGKILLed at a fixed fraction of
            the schedule and restarted mid-run; the producer keeps its schedule
            and retries, recording every attempt

Raw per-job outcomes and latencies are dumped for every job of every run; failed
submits, retries and any non-terminal jobs are retained. Nothing is generalised
from the Python reference — every number here comes from this Java service.

Usage:
  mvn -q package -DskipTests
  python3 tools/measure.py --out results/p04-04-measurement --runs 3 \
      --jobs 120 --rate 30 --kill-frac 0.5

Exit: 0 when every run drained with no lost job, 1 otherwise.
"""
import argparse
import csv
import datetime
import hashlib
import json
import math
import os
import platform
import shutil
import signal
import socket
import statistics
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JAR = os.path.join(ROOT, "target", "flowledger-0.1.0.jar")
CONTAINER = "p04-flowledger-postgres-1"
PORT = 18084
FAILURES = []


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def say(line):
    print(f"{datetime.datetime.now(datetime.timezone.utc).strftime('%H:%M:%S.%f')[:-3]} {line}",
          flush=True)


def fail(msg):
    FAILURES.append(msg)
    say(f"FAIL: {msg}")


def ok(msg):
    say(f"PASS: {msg}")


def run_cmd(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def sql(query):
    r = run_cmd(["docker", "exec", CONTAINER, "psql", "-U", "flowledger", "-d", "flowledger",
                 "-tA", "-v", "ON_ERROR_STOP=1", "-c", query])
    if r.returncode != 0:
        raise RuntimeError(f"sql failed: {query}\n{r.stderr}")
    return r.stdout.strip()


def sql_csv(query):
    """Run a query and return CSV text (psql --csv)."""
    r = run_cmd(["docker", "exec", CONTAINER, "psql", "-U", "flowledger", "-d", "flowledger",
                 "--csv", "-v", "ON_ERROR_STOP=1", "-c", query])
    if r.returncode != 0:
        raise RuntimeError(f"sql failed: {query}\n{r.stderr}")
    return r.stdout


def reset_db():
    sql("TRUNCATE attempts, results, outbox_events, downstream_effects, consumer_seen, jobs CASCADE;")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def http(port, method, path, body=None, headers=None, timeout=5):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=json.dumps(body).encode() if body is not None else None,
        method=method)
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
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


def start_app(log_path, extra_args=()):
    args = ["java", "-jar", JAR, f"--server.port={PORT}", "--flowledger.worker.leaseMillis=3000",
            *extra_args]
    fh = open(log_path, "w")
    proc = subprocess.Popen(args, stdout=fh, stderr=subprocess.STDOUT, cwd=ROOT)
    proc._log_fh = fh
    proc._log_path = log_path
    return proc


def stop_app(proc, hard=False):
    if proc is None or proc.poll() is not None:
        code = proc.returncode if proc is not None else None
    elif hard:
        proc.kill()
        code = proc.wait(timeout=15)
    else:
        proc.terminate()
        try:
            code = proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()
            code = proc.wait(timeout=15)
    fh = getattr(proc, "_log_fh", None)
    if fh:
        fh.close()
        proc._log_fh = None
    return code


def percentile(values, pct):
    if not values:
        return None
    ordered = sorted(values)
    k = max(0, min(len(ordered) - 1, int(math.ceil(pct / 100.0 * len(ordered))) - 1))
    return ordered[k]


def dump_jobs(out_path):
    """Raw per-job rows: outcome, attempts, and end-to-end latency."""
    text = sql_csv(
        "SELECT id, status, lease_generation,"
        " (SELECT count(*) FROM attempts a WHERE a.job_id = jobs.id) AS attempts,"
        " created_at, updated_at,"
        " CASE WHEN status = 'SUCCEEDED'"
        "   THEN round(EXTRACT(EPOCH FROM (updated_at - created_at)) * 1000)::bigint"
        "   ELSE NULL END AS latency_ms"
        " FROM jobs ORDER BY created_at")
    with open(out_path, "w") as fh:
        fh.write(text)
    return list(csv.DictReader(text.splitlines()))


def produce(out_dir, n_jobs, rate, run_label, budget_sec=120):
    """One fixed producer schedule. Returns (submit_log_rows, schedule).

    The schedule is time-based and identical across runs; when the service is
    unavailable the producer retries rather than shifting its schedule, and every
    attempt is recorded. `budget_sec` bounds the whole loop so an outage cannot
    turn into an unbounded retry storm.
    """
    interval = 1.0 / rate
    rows = []
    start = time.time()
    deadline = start + budget_sec

    for i in range(n_jobs):
        target = start + i * interval
        delay = target - time.time()
        if delay > 0:
            time.sleep(delay)
        key = f"load-{run_label}-{i}"
        payload = {"type": "echo", "payload": {"run": run_label, "i": i}}
        attempt = 0
        while True:
            attempt += 1
            t_submit = time.time()
            try:
                status, body = http(PORT, "POST", "/jobs", body=payload,
                                    headers={"Idempotency-Key": key})
            except OSError as e:
                status, body = -1, {"error": f"{type(e).__name__}: {e}"}
            if status in (200, 201):
                rows.append({
                    "logical": i, "key": key, "attempt": attempt,
                    "submit_ts": f"{t_submit - start:.6f}",
                    "http_status": status,
                    "job_id": body.get("jobId", ""),
                    "note": "retried" if attempt > 1 else "first_try",
                })
                break
            if time.time() > deadline:
                rows.append({
                    "logical": i, "key": key, "attempt": attempt,
                    "submit_ts": f"{t_submit - start:.6f}",
                    "http_status": status,
                    "job_id": "",
                    "note": "SUBMIT_FAILED",
                })
                fail(f"{run_label}: logical job {i} gave up after {attempt} attempts "
                     f"(last status {status}, budget exhausted)")
                break
            time.sleep(0.4)
    schedule = {"jobs": n_jobs, "rate_per_sec": rate, "interval_sec": interval,
                "started_at": f"{start:.6f}", "wall_sec": round(time.time() - start, 3),
                "budget_sec": budget_sec}
    return rows, schedule


def drain(out_dir, n_jobs, label, timeout=90):
    def complete():
        try:
            pending = int(sql(
                "SELECT count(*) FROM jobs WHERE status NOT IN ('SUCCEEDED','DEAD_LETTER')"))
        except RuntimeError:
            return False
        return pending == 0
    drained = wait_for(complete, timeout)
    if not drained:
        fail(f"{label}: {timeout}s elapsed with jobs still non-terminal")
    else:
        ok(f"{label}: all {n_jobs} jobs reached a terminal state")
    return drained


def summarise(job_rows, submit_rows):
    latencies = [int(r["latency_ms"]) for r in job_rows
                 if r["status"] == "SUCCEEDED" and r["latency_ms"]]
    by_status = {}
    for r in job_rows:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
    retried = sum(1 for r in submit_rows if r["attempt"] > 1)
    failed_submits = sum(1 for r in submit_rows if r["note"] == "SUBMIT_FAILED")
    return {
        "jobs_total": len(job_rows),
        "by_status": by_status,
        "succeeded": by_status.get("SUCCEEDED", 0),
        "non_terminal_or_failed": sum(v for k, v in by_status.items() if k != "SUCCEEDED"),
        "submit_rows": len(submit_rows),
        "submit_retries": retried,
        "submit_failures": failed_submits,
        "latency_ms": {
            "count": len(latencies),
            "min": min(latencies) if latencies else None,
            "p50": percentile(latencies, 50),
            "p95": percentile(latencies, 95),
            "p99": percentile(latencies, 99),
            "max": max(latencies) if latencies else None,
            "mean": round(statistics.mean(latencies), 2) if latencies else None,
        },
    }


def hardware_manifest(args, run_id, out_dir):
    def cpu_model():
        if sys.platform == "darwin":
            return run_cmd(["sysctl", "-n", "hw.model"]).stdout.strip()
        try:
            with open("/proc/cpuinfo") as fh:
                for line in fh:
                    if line.startswith("model name"):
                        return line.split(":", 1)[1].strip()
        except OSError:
            pass
        return "unknown"

    def mem_bytes():
        if sys.platform == "darwin":
            out = run_cmd(["sysctl", "-n", "hw.memsize"]).stdout.strip()
            return int(out) if out.isdigit() else None
        return None

    manifest = {
        "run_id": run_id,
        "captured_at_utc": utcnow(),
        "command": " ".join([os.path.basename(sys.executable)] + sys.argv),
        "out_dir": out_dir,
        "schedule": {"jobs": args.jobs, "rate_per_sec": args.rate, "runs": args.runs,
                     "kill_frac": args.kill_frac,
                     "identical_for": ["baseline", "fault"]},
        "hardware": {
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "cpu_model": cpu_model(),
            "cpu_count": os.cpu_count(),
            "memory_bytes": mem_bytes(),
        },
        "software": {
            "python": sys.version.split()[0],
            "java": run_cmd("java -version 2>&1 | head -1", shell=True).stdout.strip(),
            "maven": run_cmd("mvn -v | head -1", shell=True).stdout.strip(),
            "postgres": run_cmd(
                "docker inspect -f '{{.Config.Image}} {{.State.Status}}' " + CONTAINER,
                shell=True).stdout.strip(),
        },
        "source": {
            "jar": JAR,
            "jar_sha256": sha256(JAR) if os.path.exists(JAR) else None,
            "harness_sha256": sha256(os.path.abspath(__file__)),
            "git_commit": run_cmd(["git", "rev-parse", "HEAD"],
                                  cwd=ROOT).stdout.strip() or None,
            "git_dirty_files": run_cmd(["git", "status", "--porcelain"],
                                       cwd=ROOT).stdout.count("\n"),
        },
    }
    return manifest


def run_one(label, args, out_root):
    run_dir = os.path.join(out_root, label)
    os.makedirs(run_dir, exist_ok=True)
    reset_db()
    say(f"{label}: database truncated for this run")

    proc = start_app(os.path.join(run_dir, "app.log"))
    if not wait_ready(PORT, 90):
        stop_app(proc, hard=True)
        fail(f"{label}: application never became healthy")
        return None
    proc_holder = [proc]
    events = {"killed_at": None, "exit_code": None, "restarted": False,
              "restart_failed": False}

    if label.startswith("fault"):
        kill_at = round((args.jobs / args.rate) * args.kill_frac, 3)

        def crash_and_restart():
            time.sleep(kill_at)
            p = proc_holder[0]
            if p is not None and p.poll() is None:
                say(f"{label}: SIGKILL at t+{kill_at:.2f}s (scheduled crash)")
                p.kill()
                events["exit_code"] = p.wait(timeout=15)
                events["killed_at"] = kill_at
                fh = getattr(p, "_log_fh", None)
                if fh:
                    fh.close()
                    p._log_fh = None
            else:
                fail(f"{label}: scheduled SIGKILL at t+{kill_at:.2f}s found no live process")
            # The producer keeps its schedule across the outage, so restart while
            # it is still retrying rather than after it gives up.
            time.sleep(1.5)
            say(f"{label}: restarting after the scheduled crash")
            new = start_app(os.path.join(run_dir, "app-restart.log"))
            proc_holder[0] = new
            if wait_ready(PORT, 90):
                events["restarted"] = True
                say(f"{label}: application restarted")
            else:
                events["restart_failed"] = True
                fail(f"{label}: application did not come back after the crash")

        threading.Thread(target=crash_and_restart, daemon=True).start()

    submit_rows, schedule = produce(run_dir, args.jobs, args.rate, label)
    if label.startswith("fault"):
        if events["killed_at"] is None:
            fail(f"{label}: scheduled SIGKILL never fired")
        else:
            ok(f"{label}: process was killed as scheduled (exit {events['exit_code']})")
        if events["restarted"]:
            ok(f"{label}: application restarted mid-schedule")
        elif not events["restart_failed"]:
            fail(f"{label}: restart thread had not finished when the producer did")
    else:
        if proc_holder[0].poll() is not None:
            fail(f"{label}: application exited unexpectedly "
                 f"(code {proc_holder[0].returncode})")

    drained = drain(run_dir, args.jobs, label)
    job_rows = dump_jobs(os.path.join(run_dir, "jobs.csv"))
    with open(os.path.join(run_dir, "submit_log.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["logical", "key", "attempt", "submit_ts",
                                           "http_status", "job_id", "note"])
        w.writeheader()
        w.writerows(submit_rows)

    summary = summarise(job_rows, submit_rows)
    summary.update({"label": label, "schedule": schedule,
                    "process_killed": bool(events["killed_at"]),
                    "killed_at_sec": events["killed_at"],
                    "restarted": events["restarted"],
                    "drained": drained,
                    "app_exit_code": stop_app(proc_holder[0])})
    with open(os.path.join(run_dir, "run.json"), "w") as fh:
        json.dump(summary, fh, indent=2)
        fh.write("\n")
    say(f"{label}: succeeded={summary['succeeded']}/{summary['jobs_total']} "
        f"p50={summary['latency_ms']['p50']}ms p95={summary['latency_ms']['p95']}ms "
        f"retries={summary['submit_retries']}")

    if summary["succeeded"] != args.jobs:
        fail(f"{label}: only {summary['succeeded']}/{args.jobs} jobs succeeded "
             f"(status breakdown {summary['by_status']})")
    else:
        ok(f"{label}: all {args.jobs} jobs succeeded")
    if summary["submit_failures"]:
        fail(f"{label}: {summary['submit_failures']} submits failed permanently")
    return summary


def resolve_out_dir(base):
    """Never overwrite an earlier measurement: failed runs must stay on disk.

    A directory that has never produced a manifest/summary (e.g. one pre-seeded
    with other card evidence) is reusable; anything else is preserved and the
    next attempt gets its own directory.
    """
    if not os.path.exists(base):
        os.makedirs(base)
        return base, 0
    if not (os.path.exists(os.path.join(base, "manifest.json"))
            or os.path.exists(os.path.join(base, "summary.json"))):
        return base, 0
    n = 2
    while os.path.exists(f"{base}.attempt-{n}"):
        n += 1
    target = f"{base}.attempt-{n}"
    os.makedirs(target)
    return target, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "p04-04-measurement"))
    ap.add_argument("--runs", type=int, default=3)
    # Defaults are capacity-matched so the service runs in genuine steady state:
    # the worker leases one job per 500ms tick (~2 jobs/s), so 1.5/s sustains
    # without an ever-growing queue. Raise --rate to measure backlog behaviour.
    ap.add_argument("--jobs", type=int, default=45)
    ap.add_argument("--rate", type=float, default=1.5)
    ap.add_argument("--kill-frac", type=float, default=0.5)
    args = ap.parse_args()

    if not os.path.exists(JAR):
        print(f"jar not found: {JAR}  (run: mvn -q package -DskipTests)", file=sys.stderr)
        return 2

    out_root, attempt = resolve_out_dir(args.out)
    say(f"evidence directory: {out_root}" + (f" (attempt {attempt})" if attempt else ""))
    manifest = hardware_manifest(args, os.path.basename(out_root), out_root)
    with open(os.path.join(out_root, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
        fh.write("\n")

    results = {"baseline": [], "fault": []}
    for r in range(1, args.runs + 1):
        for label in ("baseline", "fault"):
            say(f"=== run {r}/{args.runs} — {label} ===")
            res = run_one(f"{label}", args, out_root)
            # keep each pair in its own numbered directory
            if res is not None:
                pair_dir = os.path.join(out_root, f"{label}-run-{r}")
                os.rename(os.path.join(out_root, label), pair_dir)
                res["dir"] = os.path.basename(pair_dir)
                results[label].append(res)
            else:
                say(f"{label} run {r} produced no summary (see failures)")

    summary = {
        "run_id": os.path.basename(out_root),
        "captured_at_utc": utcnow(),
        "schedule": {"jobs": args.jobs, "rate_per_sec": args.rate, "runs": args.runs,
                     "kill_frac": args.kill_frac,
                     "note": "identical producer schedule for baseline and fault"},
        "baseline": results["baseline"],
        "fault": results["fault"],
        "failures": FAILURES,
    }
    with open(os.path.join(out_root, "summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2)
        fh.write("\n")

    exit_code = 1 if FAILURES else 0
    with open(os.path.join(out_root, "exit-status.txt"), "w") as fh:
        fh.write(f"failures={len(FAILURES)}\nexit={exit_code}\n")
    say(f"done: {len(FAILURES)} failure(s), exit {exit_code}")
    for f in FAILURES:
        say(f"  FAIL {f}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
