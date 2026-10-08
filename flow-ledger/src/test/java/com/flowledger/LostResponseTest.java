package com.flowledger;

import static org.junit.jupiter.api.Assertions.*;

import com.flowledger.downstream.MockDownstream;
import com.flowledger.service.JobService;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;

@SpringBootTest(
    properties = {"flowledger.worker.enabled=false", "flowledger.relay.enabled=false"})
public class LostResponseTest {
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
  void downstreamCommitWithLostResponseDedupes() {
    String key = "key-" + UUID.randomUUID();
    var r = jobs.submit(key, "echo", "{\"x\":1}");
    var leased = jobs.leaseJob(r.jobId(), "w1", 10000);
    long gen = ((Number) leased.get("lease_generation")).longValue();
    String dedup = r.jobId() + ":op-1";
    jobs.downstream().loseResponseNext = true;
    assertThrows(
        MockDownstream.LostResponseException.class,
        () -> jobs.downstream().execute(dedup, r.jobId(), "{\"x\":1}"));
    jobs.failAttempt(r.jobId(), gen, "lost-response");
    var leased2 = jobs.leaseJob(r.jobId(), "w2", 10000);
    long gen2 = ((Number) leased2.get("lease_generation")).longValue();
    var effect = jobs.downstream().execute(dedup, r.jobId(), "{\"x\":1}");
    assertTrue(effect.wasReplay());
    jobs.completeWithGeneration(r.jobId(), "w2", gen2, dedup, effect.output());
    Long n =
        jdbc.queryForObject(
            "SELECT count(*) FROM downstream_effects WHERE dedup_key=?", Long.class, dedup);
    assertEquals(1L, n);
    assertEquals("SUCCEEDED", jobs.get(r.jobId()).get("status"));
  }
}
