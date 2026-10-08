package com.flowledger.downstream;

import java.util.Map;
import java.util.UUID;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;
import com.fasterxml.jackson.databind.ObjectMapper;

/**
 * Mock downstream that durably deduplicates on dedup_key.
 * Simulates: optional fail-first and lose-response-after-commit faults.
 */
@Component
public class MockDownstream {
  private final JdbcTemplate jdbc;
  private final ObjectMapper mapper = new ObjectMapper();
  public volatile boolean failNext = false;
  public volatile boolean loseResponseNext = false;

  public MockDownstream(JdbcTemplate jdbc) {
    this.jdbc = jdbc;
  }

  public record Effect(String output, boolean wasReplay) {}

  public Effect execute(String dedupKey, UUID jobId, String payload) {
    // Replay check first: if key exists, return stored output without re-executing.
    var existing =
        jdbc.query(
            "SELECT output FROM downstream_effects WHERE dedup_key = ?",
            rs -> rs.next() ? rs.getString(1) : null,
            dedupKey);
    if (existing != null) {
      return new Effect(existing, true);
    }
    if (failNext) {
      failNext = false;
      throw new RuntimeException("injected downstream 500");
    }
    String output;
    try {
      output =
          mapper.writeValueAsString(
              Map.of("echo", payload == null ? "" : payload, "jobId", jobId.toString()));
    } catch (Exception e) {
      throw new RuntimeException(e);
    }
    try {
      jdbc.update(
          "INSERT INTO downstream_effects(dedup_key, job_id, output) VALUES (?,?,CAST(? AS jsonb))",
          dedupKey, jobId, output);
    } catch (DuplicateKeyException dup) {
      // Lost race: another worker committed first. Return stored row.
      String stored =
          jdbc.queryForObject(
              "SELECT output FROM downstream_effects WHERE dedup_key = ?", String.class, dedupKey);
      return new Effect(stored, true);
    }
    if (loseResponseNext) {
      // Commit happened, but response is "lost" — caller sees an exception and must retry
      // with the same dedup key, which will then hit the replay path above.
      loseResponseNext = false;
      throw new LostResponseException("injected lost response after commit");
    }
    return new Effect(output, false);
  }

  public static class LostResponseException extends RuntimeException {
    public LostResponseException(String m) {
      super(m);
    }
  }
}
