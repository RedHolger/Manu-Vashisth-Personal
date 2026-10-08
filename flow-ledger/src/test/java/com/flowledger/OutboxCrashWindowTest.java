package com.flowledger;

import static org.junit.jupiter.api.Assertions.*;

import com.flowledger.service.JobService;
import com.flowledger.service.OutboxRelay;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;

/**
 * Gate: outbox crash between consumer acceptance and dispatched-mark. Env: real PG, worker
 * disabled, relay enabled (manual tick). Simulates: consumer INSERT accepted, crash before
 * UPDATE dispatched=TRUE. Assertions: replay still yields exactly one consumer effect and
 * dispatched=TRUE.
 */
@SpringBootTest(properties = {"flowledger.worker.enabled=false"})
public class OutboxCrashWindowTest {
  @Autowired JobService jobs;
  @Autowired OutboxRelay relay;
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
  void crashBetweenAcceptAndMarkStillExactlyOnce() {
    var r = jobs.submit("key-" + UUID.randomUUID(), "echo", "{}");
    var leased = jobs.leaseJob(r.jobId(), "w1", 10000);
    long gen = ((Number) leased.get("lease_generation")).longValue();
    String dedup = r.jobId() + ":op-1";
    var effect = jobs.downstream().execute(dedup, r.jobId(), "{}");
    jobs.completeWithGeneration(r.jobId(), "w1", gen, dedup, effect.output());
    UUID eventId =
        jdbc.queryForObject(
            "SELECT id FROM outbox_events WHERE job_id=?", UUID.class, r.jobId());
    // Crash window: consumer accepted but dispatched flag never set.
    jdbc.update("INSERT INTO consumer_seen(event_id) VALUES (?)", eventId);
    assertEquals(
        Boolean.FALSE,
        jdbc.queryForObject(
            "SELECT dispatched FROM outbox_events WHERE id=?", Boolean.class, eventId));
    relay.tick(); // replay: INSERT hits duplicate -> still marks dispatched
    assertEquals(
        Boolean.TRUE,
        jdbc.queryForObject(
            "SELECT dispatched FROM outbox_events WHERE id=?", Boolean.class, eventId));
    Long seen =
        jdbc.queryForObject(
            "SELECT count(*) FROM consumer_seen WHERE event_id=?", Long.class, eventId);
    assertEquals(1L, seen, "one logical consumer effect despite replay");
  }
}
