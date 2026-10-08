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

@SpringBootTest(properties = {"flowledger.worker.enabled=false"})
public class OutboxTest {
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
  void commitAndDispatchExactlyOnce() {
    String key = "key-" + UUID.randomUUID();
    var r = jobs.submit(key, "echo", "{}");
    var leased = jobs.leaseJob(r.jobId(), "w1", 10000);
    long gen = ((Number) leased.get("lease_generation")).longValue();
    String dedup = r.jobId() + ":op-1";
    var effect = jobs.downstream().execute(dedup, r.jobId(), "{}");
    jobs.completeWithGeneration(r.jobId(), "w1", gen, dedup, effect.output());
    relay.killBeforeDispatch = true;
    relay.tick();
    relay.tick();
    relay.tick();
    Long seen =
        jdbc.queryForObject(
            "SELECT count(*) FROM consumer_seen WHERE event_id IN (SELECT id FROM outbox_events WHERE job_id=?)",
            Long.class, r.jobId());
    assertEquals(1L, seen);
  }
}
