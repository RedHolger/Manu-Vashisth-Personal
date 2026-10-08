package com.flowledger;

import static org.junit.jupiter.api.Assertions.*;

import com.flowledger.service.JobService;
import java.util.ArrayList;
import java.util.UUID;
import java.util.concurrent.*;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;

/**
 * Gate: concurrent submissions (overlapping same key, conflicting payloads). Env: real PG
 * 5433, worker/relay disabled. Assertions: exactly one jobs row; every response is either the
 * winner jobId or 409; no orphan attempts/results/outbox for losers.
 */
@SpringBootTest(
    properties = {"flowledger.worker.enabled=false", "flowledger.relay.enabled=false"})
public class ConcurrentConflictTest {
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
  void overlappingConflictingSubmitsOneWinnerNoOrphans() throws Exception {
    String key = "key-" + UUID.randomUUID();
    String bodyA = "{\"order\":1}";
    String bodyB = "{\"order\":2}";
    var pool = Executors.newFixedThreadPool(8);
    var tasks = new ArrayList<Callable<String>>();
    for (int i = 0; i < 4; i++) {
      tasks.add(
          () -> {
            try {
              return "OK:" + jobs.submit(key, "echo", bodyA).jobId();
            } catch (JobService.ConflictException c) {
              return "CONFLICT";
            }
          });
      tasks.add(
          () -> {
            try {
              return "OK:" + jobs.submit(key, "echo", bodyB).jobId();
            } catch (JobService.ConflictException c) {
              return "CONFLICT";
            }
          });
    }
    var futures = pool.invokeAll(tasks);
    pool.shutdown();
    assertTrue(pool.awaitTermination(30, TimeUnit.SECONDS));
    String winner = null;
    int ok = 0, conflict = 0;
    for (var f : futures) {
      String r = f.get(10, TimeUnit.SECONDS);
      if (r.startsWith("OK:")) {
        ok++;
        String id = r.substring(3);
        if (winner == null) winner = id;
        assertEquals(winner, id, "all OK responses must agree on one job");
      } else {
        conflict++;
        assertEquals("CONFLICT", r);
      }
    }
    assertTrue(ok >= 1, "one payload family must win");
    assertTrue(conflict >= 1, "losing family must see 409");
    Long n =
        jdbc.queryForObject(
            "SELECT count(*) FROM jobs WHERE idempotency_key=?", Long.class, key);
    assertEquals(1L, n, "exactly one logical job");
    // No orphaned child rows beyond the single winner job.
    Long jobs = jdbc.queryForObject("SELECT count(*) FROM jobs", Long.class);
    Long attempts = jdbc.queryForObject("SELECT count(*) FROM attempts", Long.class);
    assertEquals(1L, jobs);
    assertEquals(0L, attempts, "submit creates no attempts");
  }
}
