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
 * Gate: payload validation minimum. Env: service-level (controller maps
 * ValidationException -> HTTP 400). Assertions: unsupported/blank type, invalid JSON,
 * blank key rejected; allowed types echo/export/poison accepted.
 */
@SpringBootTest(
    properties = {"flowledger.worker.enabled=false", "flowledger.relay.enabled=false"})
public class ValidationTest {
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
  void rejectsMalformedAndUnsupported() {
    String key = "key-" + UUID.randomUUID();
    assertThrows(
        JobService.ValidationException.class, () -> jobs.submit(key, "nope", "{}"));
    assertThrows(JobService.ValidationException.class, () -> jobs.submit(key, "", "{}"));
    assertThrows(JobService.ValidationException.class, () -> jobs.submit(key, "echo", "{bad"));
    assertThrows(JobService.ValidationException.class, () -> jobs.submit("  ", "echo", "{}"));
    assertThrows(JobService.ValidationException.class, () -> jobs.submit(null, "echo", "{}"));
    assertEquals(0L, jdbc.queryForObject("SELECT count(*) FROM jobs", Long.class));
  }

  @Test
  void acceptsAllowedTypes() {
    for (String type : new String[] {"echo", "export", "poison"}) {
      var r = jobs.submit("key-" + UUID.randomUUID(), type, "{\"a\":1}");
      assertNotNull(r.jobId());
    }
  }

  @Test
  void idempotencyComparesExactPayloadString() {
    // Documents: semantically-equal JSON with different key order hashes differently
    // (re-serialized bytes, order-sensitive) -> 409. Canonicalization deferred.
    String key = "key-" + UUID.randomUUID();
    jobs.submit(key, "echo", "{\"a\":1,\"b\":2}");
    assertThrows(
        JobService.ConflictException.class,
        () -> jobs.submit(key, "echo", "{\"b\":2,\"a\":1}"));
  }
}
