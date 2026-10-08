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
public class LeaseGenerationTest {
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
  void staleGenerationRejected() {
    String key = "key-" + UUID.randomUUID();
    var r = jobs.submit(key, "echo", "{}");
    var leased = jobs.leaseJob(r.jobId(), "w1", 10000);
    assertNotNull(leased);
    long gen = ((Number) leased.get("lease_generation")).longValue();
    jobs.failAttempt(r.jobId(), gen, "release-for-takeover");
    var leased2 = jobs.leaseJob(r.jobId(), "w2", 10000);
    assertNotNull(leased2);
    long gen2 = ((Number) leased2.get("lease_generation")).longValue();
    assertTrue(gen2 > gen);
    assertThrows(
        JobService.StaleLeaseException.class,
        () -> jobs.completeWithGeneration(r.jobId(), "w1", gen, r.jobId() + ":op-1", "{\"ok\":1}"));
  }
}
