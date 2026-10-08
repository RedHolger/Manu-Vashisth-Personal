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
 * Gate: submission atomicity. Env: real PG, worker/relay disabled. submit() performs exactly
 * ONE write (INSERT INTO jobs). Assertions: after submit, one jobs row and zero
 * attempts/results/outbox/downstream rows for that job — no partial multi-table state possible.
 */
@SpringBootTest(
    properties = {"flowledger.worker.enabled=false", "flowledger.relay.enabled=false"})
public class SubmissionAtomicityTest {
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
  void submitWritesOnlyJobsRow() {
    String key = "key-" + UUID.randomUUID();
    var r = jobs.submit(key, "echo", "{\"a\":1}");
    assertEquals(
        1L, jdbc.queryForObject("SELECT count(*) FROM jobs WHERE id=?", Long.class, r.jobId()));
    assertEquals(
        0L,
        jdbc.queryForObject(
            "SELECT count(*) FROM attempts WHERE job_id=?", Long.class, r.jobId()));
    assertEquals(
        0L,
        jdbc.queryForObject(
            "SELECT count(*) FROM results WHERE job_id=?", Long.class, r.jobId()));
    assertEquals(
        0L,
        jdbc.queryForObject(
            "SELECT count(*) FROM outbox_events WHERE job_id=?", Long.class, r.jobId()));
    assertEquals(
        0L,
        jdbc.queryForObject(
            "SELECT count(*) FROM downstream_effects WHERE job_id=?", Long.class, r.jobId()));
  }

  @Test
  void failedValidationWritesNothing() {
    String key = "key-" + UUID.randomUUID();
    assertThrows(
        JobService.ValidationException.class,
        () -> jobs.submit(key, "nope", "{\"a\":1}"));
    assertEquals(0L, jdbc.queryForObject("SELECT count(*) FROM jobs", Long.class));
  }
}
