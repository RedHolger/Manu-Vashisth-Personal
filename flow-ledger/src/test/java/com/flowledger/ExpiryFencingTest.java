package com.flowledger;

import static org.junit.jupiter.api.Assertions.*;

import com.flowledger.service.JobService;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;

/**
 * Gate: expired-worker fencing via REAL expiry (not failAttempt shortcut). Env: real PG,
 * worker/relay disabled. A leases gen1; test expires A's lease with SQL (keeps LEASED); B
 * leases gen2; A's commit with gen1 is rejected STALE; B completes.
 */
@SpringBootTest(
    properties = {"flowledger.worker.enabled=false", "flowledger.relay.enabled=false"})
public class ExpiryFencingTest {
  @Autowired JobService jobs;
  @Autowired JdbcTemplate jdbc;

  @BeforeEach
  void clean() {
    jdbc.update("DELETE FROM consumer_seen");
    jdbc.update("DELETE FROM outbox_events");
    jdbc.update("DELETE FROM results");
    jdbc.update("DELETE FROM attempts");
    jdbc.update("DELETE FROM downstream_effects");
    jdbc.update("DELETE FROM jobs");
  }

  @Test
  void expiredLeaseTakeoverFencesStaleWorker() {
    var r = jobs.submit("key-" + UUID.randomUUID(), "echo", "{}");
    var a = jobs.leaseJob(r.jobId(), "worker-A", 10000);
    long genA = ((Number) a.get("lease_generation")).longValue();
    // Real expiry: lease lapses while A is still "running".
    jdbc.update(
        "UPDATE jobs SET lease_expiry=now()-interval '1 second' WHERE id=?", r.jobId());
    var b = jobs.leaseJob(r.jobId(), "worker-B", 10000);
    assertNotNull(b);
    long genB = ((Number) b.get("lease_generation")).longValue();
    assertTrue(genB > genA);
    // A resumes late and tries to commit with its stale generation.
    assertThrows(
        JobService.StaleLeaseException.class,
        () -> jobs.completeWithGeneration(r.jobId(), "worker-A", genA, r.jobId() + ":op-1", "{\"ok\":1}"));
    // B completes with current generation.
    String dedup = r.jobId() + ":op-1";
    var effect = jobs.downstream().execute(dedup, r.jobId(), "{}");
    jobs.completeWithGeneration(r.jobId(), "worker-B", genB, dedup, effect.output());
    assertEquals("SUCCEEDED", jobs.get(r.jobId()).get("status"));
    Long n =
        jdbc.queryForObject(
            "SELECT count(*) FROM downstream_effects WHERE dedup_key=?", Long.class, dedup);
    assertEquals(1L, n, "exactly one logical downstream effect");
  }
}
