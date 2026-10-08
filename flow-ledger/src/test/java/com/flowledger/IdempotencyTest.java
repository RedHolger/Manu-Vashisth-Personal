package com.flowledger;

import static org.junit.jupiter.api.Assertions.*;

import com.flowledger.service.JobService;
import java.util.UUID;
import java.util.concurrent.*;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;

@SpringBootTest(
    properties = {"flowledger.worker.enabled=false", "flowledger.relay.enabled=false"})
public class IdempotencyTest {
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
  void concurrentDuplicateSubmitsOneLogicalJob() throws Exception {
    String key = "key-" + UUID.randomUUID();
    var pool = Executors.newFixedThreadPool(8);
    var futures =
        pool.invokeAll(
            java.util.Collections.nCopies(
                8, (Callable<JobService.SubmitResult>) () -> jobs.submit(key, "echo", "{\"a\":1}")));
    pool.shutdown();
    UUID first = null;
    for (var f : futures) {
      var r = f.get();
      if (first == null) first = r.jobId();
      assertEquals(first, r.jobId());
    }
    Long n =
        jdbc.queryForObject(
            "SELECT count(*) FROM jobs WHERE idempotency_key=?", Long.class, key);
    assertEquals(1L, n);
  }

  @Test
  void sameKeyDifferentBodyConflicts() {
    String key = "key-" + UUID.randomUUID();
    jobs.submit(key, "echo", "{\"a\":1}");
    assertThrows(
        JobService.ConflictException.class, () -> jobs.submit(key, "echo", "{\"a\":2}"));
  }
}
