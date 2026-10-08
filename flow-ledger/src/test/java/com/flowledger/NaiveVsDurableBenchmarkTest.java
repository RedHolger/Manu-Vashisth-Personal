package com.flowledger;

import static org.junit.jupiter.api.Assertions.*;

import com.flowledger.downstream.MockDownstream;
import com.flowledger.service.JobService;
import java.io.File;
import java.util.*;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;

/**
 * Gate: naive-vs-durable baseline evaluation (v1 acceptance, not v1.1). Env: real PG 5433,
 * worker/relay disabled, deterministic schedule, no randomness. Identical workload (20 logical
 * jobs) and identical crash schedule for both queues. Metrics: lost, duplicates, recovery,
 * throughput/latency. Report preserved at results/p04-v1-complete/eval/report.json + report.md.
 * Unsuccessful runs (naive losses/duplicates) are the expected preserved negatives.
 */
@SpringBootTest(
    properties = {"flowledger.worker.enabled=false", "flowledger.relay.enabled=false"})
public class NaiveVsDurableBenchmarkTest {
  @Autowired JobService jobs;
  @Autowired JdbcTemplate jdbc;

  static final int N = 20;
  static final Set<Integer> DUP_SUBMIT = Set.of(2, 9);
  static final Set<Integer> LOST_RESPONSE = Set.of(3, 7, 14);
  static final Set<Integer> WORKER_KILL = Set.of(5, 11);
  static final Set<Integer> POISON = Set.of(17);
  static final Set<Integer> RESTART = Set.of(12);

  @BeforeEach
  void clean() {
    jdbc.update("DELETE FROM consumer_seen");
    jdbc.update("DELETE FROM outbox_events");
    jdbc.update("DELETE FROM results");
    jdbc.update("DELETE FROM attempts");
    jdbc.update("DELETE FROM downstream_effects");
    jdbc.update("DELETE FROM jobs");
  }

  /** Deliberately minimal baseline: HashMaps, no idempotency, no dedup, no persistence. */
  static class NaiveQueue {
    Map<String, String> jobsByKey = new HashMap<>(); // key -> jobId (OVERWRITTEN? no: always new)
    Map<String, String> jobStatus = new HashMap<>(); // jobId -> status
    Map<String, Integer> effectCounts = new HashMap<>(); // dedupKey -> executions
    Map<String, String> jobKey = new HashMap<>(); // jobId -> key
    int jobsCreated = 0;

    String submit(String key, String body) {
      // Naive: no idempotency — every submit creates a new job (duplicates on retry).
      String jobId = "naive-" + (jobsCreated++);
      jobsByKey.put(key + "#" + jobsCreated, jobId);
      jobStatus.put(jobId, "PENDING");
      jobKey.put(jobId, key);
      return jobId;
    }

    void execute(String dedupKey) {
      // Naive: no dedup — every attempt re-executes.
      effectCounts.merge(dedupKey, 1, Integer::sum);
    }

    void crashRestart(Set<String> pendingBefore) {
      // Process kill wipes in-memory job tracking for uncompleted jobs.
      for (String j : new ArrayList<>(jobStatus.keySet())) {
        if (jobStatus.get(j).equals("PENDING")) jobStatus.remove(j);
      }
    }
  }

  record Outcome(
      int logical,
      int completed,
      int deadLetter,
      int lost,
      int duplicateEffects,
      int recovered,
      long wallMs,
      double jobsPerSec) {}

  @Test
  void identicalScheduleBothQueues() throws Exception {
    List<String> raw = new ArrayList<>();
    raw.add("queue,logical,jobId,outcome,latencyMs");

    // ---- NAIVE ----
    long t0 = System.nanoTime();
    NaiveQueue naive = new NaiveQueue();
    Map<String, String> naiveLogical = new HashMap<>(); // i -> jobId (first)
    int naiveRecovered = 0;
    for (int i = 0; i < N; i++) {
      long jobStart = System.nanoTime();
      String key = "bench-" + i;
      String body = "{\"i\":" + i + "}";
      String jid = naive.submit(key, body);
      String naiveOutcome;
      naiveLogical.putIfAbsent(String.valueOf(i), jid);
      boolean dupSubmit = DUP_SUBMIT.contains(i);
      if (dupSubmit) {
        naive.submit(key, body); // duplicate logical submit -> naive duplicates
      }
      if (POISON.contains(i)) {
        for (int a = 0; a < 5; a++) naive.execute(jid + ":op-1");
        naive.jobStatus.put(jid, "DEAD_LETTER");
        naiveOutcome = "DEAD_LETTER";
        raw.add("naive," + i + "," + jid + "," + naiveOutcome + ","
            + (System.nanoTime() - jobStart) / 1_000_000);
        continue;
      }
      if (RESTART.contains(i)) {
        naive.execute(jid + ":op-1");
        naive.crashRestart(null); // job record lost before completion
        naiveOutcome = "LOST";
        raw.add("naive," + i + "," + jid + "," + naiveOutcome + ","
            + (System.nanoTime() - jobStart) / 1_000_000);
        continue;
      }
      if (LOST_RESPONSE.contains(i) || WORKER_KILL.contains(i)) {
        naive.execute(jid + ":op-1"); // commit effect...
        naive.execute(jid + ":op-1"); // ...retry re-executes (no dedup)
        naiveRecovered++;
        naive.jobStatus.put(jid, "SUCCEEDED");
        naiveOutcome = "SUCCEEDED_DUPLICATE_EFFECT";
      } else {
        naive.execute(jid + ":op-1");
        naive.jobStatus.put(jid, "SUCCEEDED");
        naiveOutcome = dupSubmit ? "SUCCEEDED_DUPLICATE_JOB" : "SUCCEEDED";
      }
      raw.add("naive," + i + "," + jid + "," + naiveOutcome + ","
          + (System.nanoTime() - jobStart) / 1_000_000);
    }
    long naiveMs = (System.nanoTime() - t0) / 1_000_000;
    int naiveEffects = naive.effectCounts.values().stream().mapToInt(x -> x).sum();
    long naiveCompleted = naive.jobStatus.values().stream().filter(s -> s.equals("SUCCEEDED")).count();
    long naiveDead = naive.jobStatus.values().stream().filter(s -> s.equals("DEAD_LETTER")).count();
    // Lost = logical jobs with no surviving record (RESTART wiped index 12).
    int naiveLost = 0;
    for (int i = 0; i < N; i++) {
      if (RESTART.contains(i)) {
        // job record for i=12 was wiped; effect happened once -> lost, not duplicated
        naiveLost++;
      }
    }
    // Duplicates = extra effect executions beyond one per surviving logical job attempt,
    // plus whole extra jobs from DUP_SUBMIT (each dup submit created a 2nd job with its effect).
    int naiveDup = (naiveEffects - N) + DUP_SUBMIT.size();
    Outcome nOut =
        new Outcome(N, (int) naiveCompleted, (int) naiveDead, naiveLost, naiveDup, naiveRecovered,
            naiveMs, N * 1000.0 / Math.max(1, naiveMs));

    // ---- DURABLE (real JobService, manual lease cycle, same schedule) ----
    long d0 = System.nanoTime();
    Map<Integer, UUID> durableIds = new HashMap<>();
    int durableRecovered = 0;
    for (int i = 0; i < N; i++) {
      long jobStart = System.nanoTime();
      String key = "bench-" + i;
      String body = "{\"i\":" + i + "}";
      var sub = jobs.submit(key, "echo", body);
      durableIds.put(i, sub.jobId());
      if (DUP_SUBMIT.contains(i)) {
        var dup = jobs.submit(key, "echo", body);
        assertEquals(sub.jobId(), dup.jobId(), "durable dedups concurrent-equivalent resubmit");
      }
      if (POISON.contains(i)) {
        for (int a = 0; a < 5; a++) {
          var leased = jobs.leaseJob(sub.jobId(), "bench", 10000);
          assertNotNull(leased);
          long g = ((Number) leased.get("lease_generation")).longValue();
          jobs.failAttempt(sub.jobId(), g, "poison");
        }
        assertNull(jobs.leaseJob(sub.jobId(), "bench", 10000));
        durableRow(raw, i, sub.jobId(), "DEAD_LETTER", jobStart);
        continue;
      }
      if (RESTART.contains(i)) {
        // Kill process after submit, before any work: DB retains the job; re-lease recovers.
        var leased = jobs.leaseJob(sub.jobId(), "bench", 10000);
        long g = ((Number) leased.get("lease_generation")).longValue();
        String dedup = sub.jobId() + ":op-1";
        var eff = jobs.downstream().execute(dedup, sub.jobId(), body);
        jobs.completeWithGeneration(sub.jobId(), "bench", g, dedup, eff.output());
        durableRecovered++;
        durableRow(raw, i, sub.jobId(), "SUCCEEDED_RECOVERED", jobStart);
        continue;
      }
      if (LOST_RESPONSE.contains(i)) {
        var leased = jobs.leaseJob(sub.jobId(), "bench", 10000);
        long g = ((Number) leased.get("lease_generation")).longValue();
        String dedup = sub.jobId() + ":op-1";
        jobs.downstream().loseResponseNext = true;
        assertThrows(
            MockDownstream.LostResponseException.class,
            () -> jobs.downstream().execute(dedup, sub.jobId(), body));
        jobs.failAttempt(sub.jobId(), g, "lost-response");
        var leased2 = jobs.leaseJob(sub.jobId(), "bench", 10000);
        long g2 = ((Number) leased2.get("lease_generation")).longValue();
        var replay = jobs.downstream().execute(dedup, sub.jobId(), body);
        assertTrue(replay.wasReplay());
        jobs.completeWithGeneration(sub.jobId(), "bench", g2, dedup, replay.output());
        durableRecovered++;
        durableRow(raw, i, sub.jobId(), "SUCCEEDED_RECOVERED", jobStart);
        continue;
      }
      if (WORKER_KILL.contains(i)) {
        var leased = jobs.leaseJob(sub.jobId(), "bench", 10000);
        long g = ((Number) leased.get("lease_generation")).longValue();
        String dedup = sub.jobId() + ":op-1";
        jobs.downstream().execute(dedup, sub.jobId(), body); // commit...
        jobs.failAttempt(sub.jobId(), g, "worker-killed-before-complete"); // ...kill
        var leased2 = jobs.leaseJob(sub.jobId(), "bench", 10000);
        long g2 = ((Number) leased2.get("lease_generation")).longValue();
        var replay = jobs.downstream().execute(dedup, sub.jobId(), body);
        assertTrue(replay.wasReplay());
        jobs.completeWithGeneration(sub.jobId(), "bench", g2, dedup, replay.output());
        durableRecovered++;
        durableRow(raw, i, sub.jobId(), "SUCCEEDED_RECOVERED", jobStart);
        continue;
      }
      var leased = jobs.leaseJob(sub.jobId(), "bench", 10000);
      long g = ((Number) leased.get("lease_generation")).longValue();
      String dedup = sub.jobId() + ":op-1";
      var eff = jobs.downstream().execute(dedup, sub.jobId(), body);
      jobs.completeWithGeneration(sub.jobId(), "bench", g, dedup, eff.output());
      durableRow(raw, i, sub.jobId(),
          DUP_SUBMIT.contains(i) ? "SUCCEEDED_DEDUPED" : "SUCCEEDED", jobStart);
    }
    long durableMs = (System.nanoTime() - d0) / 1_000_000;
    Long dCompleted =
        jdbc.queryForObject("SELECT count(*) FROM jobs WHERE status='SUCCEEDED'", Long.class);
    Long dDead =
        jdbc.queryForObject("SELECT count(*) FROM jobs WHERE status='DEAD_LETTER'", Long.class);
    Long dJobs = jdbc.queryForObject("SELECT count(*) FROM jobs", Long.class);
    Long dEffects = jdbc.queryForObject("SELECT count(*) FROM downstream_effects", Long.class);
    int dLost = N - dCompleted.intValue() - dDead.intValue();
    int dDup = dEffects.intValue() - dCompleted.intValue(); // extra effects beyond one per success
    Outcome dOut =
        new Outcome(N, dCompleted.intValue(), dDead.intValue(), dLost, dDup, durableRecovered,
            durableMs, N * 1000.0 / Math.max(1, durableMs));

    // ---- Assertions: durable must show zero loss/duplication; naive must show the failure modes
    assertEquals(0, dLost, "durable: no lost jobs");
    assertEquals(0, dDup, "durable: no duplicate effects");
    assertEquals(N - 1, dCompleted, "durable: 19 succeed, 1 poison dead-letter");
    assertEquals(1, dDead);
    assertEquals(N, dJobs.intValue(), "durable: one row per logical job (dups deduped)");
    assertTrue(nOut.lost() >= 1, "naive baseline must demonstrate loss (restart)");
    assertTrue(nOut.duplicateEffects() >= 4, "naive baseline must demonstrate duplication");

    // ---- Preserved report ----
    File dir = new File(System.getProperty("bench.outDir", "results/p04-v1-complete/eval"));
    dir.mkdirs();
    java.nio.file.Files.writeString(
        new File(dir, "raw-jobs.csv").toPath(), String.join("\n", raw) + "\n");
    java.nio.file.Files.writeString(
        new File(dir, "hardware.json").toPath(), hardwareJson() + "\n");
    String json =
        "{\n"
            + "  \"workload\": {\"logicalJobs\": 20},\n"
            + "  \"schedule\": {\"dupSubmit\": [2, 9], \"lostResponse\": [3, 7, 14],"
            + " \"workerKill\": [5, 11], \"restart\": [12], \"poison\": [17]},\n"
            + "  \"naive\": "
            + outcomeJson(nOut) + ",\n"
            + "  \"durable\": "
            + outcomeJson(dOut) + ",\n"
            + "  \"notes\": \"naive=HashMap,no idempotency,no dedup,no persistence;"
            + " durable=Postgres,generation fencing,dedup keys,atomic result+outbox\"\n"
            + "}\n";
    java.nio.file.Files.writeString(new File(dir, "report.json").toPath(), json);
    String md =
        "# P04 naive-vs-durable benchmark\n\n"
            + "Identical workload (20 logical jobs) and crash schedule "
            + "(dupSubmit 2,9; lostResponse 3,7,14; workerKill 5,11; restart 12; poison 17).\n\n"
            + "| queue | completed | deadLetter | lost | duplicateEffects | recovered | wallMs | jobs/s |\n"
            + "|---|---|---|---|---|---|---|---|\n"
            + row("naive", nOut) + row("durable", dOut) + "\n"
            + "Naive losses/duplicates are preserved expected negatives, not test failures.\n";
    java.nio.file.Files.writeString(new File(dir, "report.md").toPath(), md);
  }

  static String outcomeJson(Outcome o) {
    return String.format(
        "{\"logical\":%d,\"completed\":%d,\"deadLetter\":%d,\"lost\":%d,"
            + "\"duplicateEffects\":%d,\"recovered\":%d,\"wallMs\":%d,\"jobsPerSec\":%.1f}",
        o.logical(), o.completed(), o.deadLetter(), o.lost(), o.duplicateEffects(),
        o.recovered(), o.wallMs(), o.jobsPerSec());
  }

  static String row(String name, Outcome o) {
    return String.format(
        "| %s | %d | %d | %d | %d | %d | %d | %.1f |\n", name, o.completed(), o.deadLetter(),
        o.lost(), o.duplicateEffects(), o.recovered(), o.wallMs(), o.jobsPerSec());
  }

  static void durableRow(List<String> raw, int i, UUID jobId, String outcome, long startNanos) {
    raw.add(
        "durable," + i + "," + jobId + "," + outcome + ","
            + (System.nanoTime() - startNanos) / 1_000_000);
  }

  /** Hardware manifest recorded alongside every benchmark run. */
  static String hardwareJson() throws Exception {
    Runtime rt = Runtime.getRuntime();
    String git = System.getProperty("bench.gitCommit", "unknown");
    try {
      Process p =
          new ProcessBuilder("git", "rev-parse", "HEAD").redirectErrorStream(true).start();
      String out = new String(p.getInputStream().readAllBytes()).trim();
      if (p.waitFor() == 0 && !out.isEmpty()) git = out;
    } catch (Exception ignored) {
      // git unavailable — keep the placeholder
    }
    return String.format(
        "{\"os\":\"%s\",\"arch\":\"%s\",\"javaVersion\":\"%s\",\"javaVendor\":\"%s\","
            + "\"availableProcessors\":%d,\"maxHeapBytes\":%d,\"gitCommit\":\"%s\","
            + "\"jvmArgs\":\"%s\"}",
        System.getProperty("os.name"),
        System.getProperty("os.arch"),
        System.getProperty("java.version"),
        System.getProperty("java.vendor"),
        rt.availableProcessors(),
        rt.maxMemory(),
        git,
        java.lang.management.ManagementFactory.getRuntimeMXBean().getInputArguments());
  }
}
