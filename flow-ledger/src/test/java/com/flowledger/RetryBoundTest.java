package com.flowledger;

import static org.junit.jupiter.api.Assertions.*;

import com.flowledger.service.JobService;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;

@SpringBootTest(
    properties = {"flowledger.worker.enabled=false", "flowledger.relay.enabled=false"})
public class RetryBoundTest {
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
  void poisonJobReachesDeadLetter() {
    String key = "key-" + UUID.randomUUID();
    var r = jobs.submit(key, "poison", "{}");
    for (int i = 0; i < 5; i++) {
      var leased = jobs.leaseJob(r.jobId(), "w", 100);
      assertNotNull(leased, "expected lease " + i);
      long gen = ((Number) leased.get("lease_generation")).longValue();
      jobs.failAttempt(r.jobId(), gen, "poison");
    }
    assertNull(jobs.leaseJob(r.jobId(), "w", 100));
    assertEquals("DEAD_LETTER", jobs.get(r.jobId()).get("status"));
  }
}
