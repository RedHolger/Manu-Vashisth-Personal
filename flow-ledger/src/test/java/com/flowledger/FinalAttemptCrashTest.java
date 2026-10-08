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
 * Gate: reference `test_final_attempt_crash` (see REFERENCE_TEST_MAP.md row 5). Env: real
 * PostgreSQL, worker/relay disabled. A worker claims the final allowed attempt and dies without
 * calling failAttempt or complete: each lease lapses while the job stays LEASED. Assertions: the
 * expired final claim terminates the job as DEAD_LETTER, no sixth attempt row is written, no
 * result exists, and no further lease is granted.
 */
@SpringBootTest(
    properties = {"flowledger.worker.enabled=false", "flowledger.relay.enabled=false"})
public class FinalAttemptCrashTest {
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
  void expiredFinalAttemptLeaseTerminatesAsDeadLetter() {
    var r = jobs.submit("key-" + UUID.randomUUID(), "echo", "{}");
    assertEquals("PENDING", r.status());

    for (int i = 0; i < 5; i++) {
      var leased = jobs.leaseJob(r.jobId(), "crashy-" + i, 10000);
      assertNotNull(leased, "attempt " + i + " must be claimable before the bound");
      assertEquals("LEASED", leased.get("status"));
      // The process dies here: no failAttempt, no complete. The lease simply lapses.
      jdbc.update(
          "UPDATE jobs SET lease_expiry = now() - interval '1 second' WHERE id = ?", r.jobId());
    }

    assertEquals(
        5L,
        jdbc.queryForObject("SELECT count(*) FROM attempts WHERE job_id = ?", Long.class, r.jobId()),
        "five crashed attempts recorded");

    // Expired final claim must terminate the job instead of granting a sixth attempt.
    assertNull(jobs.leaseNext("recovery-worker", 10000), "no lease once the attempt bound is hit");
    assertEquals("DEAD_LETTER", jobs.get(r.jobId()).get("status"));

    assertEquals(
        5L,
        jdbc.queryForObject("SELECT count(*) FROM attempts WHERE job_id = ?", Long.class, r.jobId()),
        "recovery must not write a sixth attempt");
    assertEquals(
        0L,
        jdbc.queryForObject("SELECT count(*) FROM results WHERE job_id = ?", Long.class, r.jobId()),
        "a dead-lettered job has no result");
    assertNull(jobs.leaseNext("recovery-worker", 10000), "DEAD_LETTER is not leaseable");
  }
}
