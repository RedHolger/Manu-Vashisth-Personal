package com.flowledger.service;

import com.flowledger.downstream.MockDownstream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class JobService {
  private final JdbcTemplate jdbc;
  private final MockDownstream downstream;
  private final int maxAttempts;

  public JobService(
      JdbcTemplate jdbc,
      MockDownstream downstream,
      @Value("${flowledger.worker.maxAttempts:5}") int maxAttempts) {
    this.jdbc = jdbc;
    this.downstream = downstream;
    this.maxAttempts = maxAttempts;
  }

  public record SubmitResult(UUID jobId, boolean created, String status) {}

  public static String hash(String s) {
    try {
      MessageDigest md = MessageDigest.getInstance("SHA-256");
      return HexFormat.of().formatHex(md.digest(s.getBytes(StandardCharsets.UTF_8)));
    } catch (Exception e) {
      throw new RuntimeException(e);
    }
  }

  // No @Transactional: single INSERT + separate re-read on race, so a
  // DuplicateKeyException does not abort a surrounding transaction.
  // Submission atomicity: submit() performs exactly ONE write (INSERT INTO jobs).
  // No attempts/results/outbox/downstream rows are created here. A single-row
  // INSERT is atomic in Postgres: a crash before commit leaves no row (client
  // retries with the same key safely); a crash after commit leaves one row
  // (retry returns the existing job). There is no multi-table partial state
  // to protect, so a surrounding transaction would add nothing and would turn
  // a concurrent DuplicateKey into a transaction-abort (see DECISIONS.md).
  // Idempotency semantics: bodyHash = SHA-256(type + "\n" + payload) where
  // payload is the exact string passed to this method. The HTTP controller
  // passes ObjectMapper-re-serialized JSON (key order as received, NOT
  // canonicalized): byte-different but semantically-equal JSON hashes
  // differently and yields 409. Canonicalization is deferred (see LIMITATIONS).
  public SubmitResult submit(String idempotencyKey, String type, String payload) {
    validateSubmit(idempotencyKey, type, payload);
    if (payload == null) payload = "{}";
    String body = type + "\n" + (payload == null ? "" : payload);
    String bodyHash = hash(body);
    List<Map<String, Object>> rows =
        jdbc.queryForList(
            "SELECT id, body_hash, status FROM jobs WHERE idempotency_key = ?", idempotencyKey);
    if (!rows.isEmpty()) {
      var r = rows.get(0);
      if (!bodyHash.equals(r.get("body_hash"))) {
        throw new ConflictException("same Idempotency-Key with different body");
      }
      return new SubmitResult(
          (UUID) r.get("id"), false, (String) r.get("status"));
    }
    UUID id = UUID.randomUUID();
    try {
      jdbc.update(
          "INSERT INTO jobs(id, idempotency_key, body_hash, type, payload, status) VALUES (?,?,?, ?,CAST(? AS jsonb),'PENDING')",
          id, idempotencyKey, bodyHash, type, payload == null ? "{}" : payload);
    } catch (DuplicateKeyException dup) {
      // Concurrent insert won the race — re-read winner.
      var r =
          jdbc.queryForMap(
              "SELECT id, body_hash, status FROM jobs WHERE idempotency_key = ?", idempotencyKey);
      if (!bodyHash.equals(r.get("body_hash"))) {
        throw new ConflictException("same Idempotency-Key with different body");
      }
      return new SubmitResult((UUID) r.get("id"), false, (String) r.get("status"));
    }
    return new SubmitResult(id, true, "PENDING");
  }

  static final java.util.Set<String> ALLOWED_TYPES =
      java.util.Set.of("echo", "export", "poison");

  /** Minimum correctness: clear client errors for malformed/unsupported jobs. */
  static void validateSubmit(String key, String type, String payload) {
    if (key == null || key.isBlank() || key.length() > 128) {
      throw new ValidationException("Idempotency-Key required (1-128 chars)");
    }
    if (type == null || type.isBlank() || type.length() > 32) {
      throw new ValidationException("type required (1-32 chars)");
    }
    if (!ALLOWED_TYPES.contains(type)) {
      throw new ValidationException(
          "unsupported type '" + type + "'; allowed: echo, export, poison");
    }
    String p = payload == null ? "{}" : payload;
    if (p.length() > 65536) {
      throw new ValidationException("payload too large (max 65536 chars)");
    }
    try {
      new com.fasterxml.jackson.databind.ObjectMapper().readTree(p);
    } catch (Exception e) {
      throw new ValidationException("payload must be valid JSON: " + e.getMessage());
    }
  }

  public Map<String, Object> get(UUID id) {
    try {
      var job = jdbc.queryForMap("SELECT * FROM jobs WHERE id = ?", id);
      var attempts =
          jdbc.queryForObject(
              "SELECT count(*) FROM attempts WHERE job_id = ?", Long.class, id);
      job.put("attempts", attempts);
      return job;
    } catch (EmptyResultDataAccessException e) {
      throw new NotFoundException("job not found");
    }
  }

  /** Lease one PENDING-or-expired job. Bumps generation monotonically. Returns null if none. */
  @Transactional
  public Map<String, Object> leaseNext(String owner, long leaseMillis) {
    // Reference parity with project.py claim(): an expired job already at the attempt
    // bound terminates to DEAD_LETTER before queue selection, so an exhausted head-of-line
    // job is retired in this call instead of occupying the oldest-eligible slot.
    jdbc.update(
        "UPDATE jobs SET status='DEAD_LETTER', updated_at=now()"
            + " WHERE status IN ('PENDING','LEASED','FAILED')"
            + " AND (lease_expiry IS NULL OR lease_expiry < now())"
            + " AND (SELECT count(*) FROM attempts a WHERE a.job_id = jobs.id) >= ?",
        maxAttempts);
    List<Map<String, Object>> rows =
        jdbc.queryForList(
            "SELECT id FROM jobs WHERE status IN ('PENDING','LEASED','FAILED')"
                + " AND (lease_expiry IS NULL OR lease_expiry < now()) ORDER BY created_at LIMIT 1 FOR UPDATE SKIP LOCKED");
    if (rows.isEmpty()) return null;
    UUID jobId = (UUID) rows.get(0).get("id");
    return leaseJob(jobId, owner, leaseMillis);
  }

  /** Deterministic lease of a specific job (for tests and targeted recovery). */
  @Transactional
  public Map<String, Object> leaseJob(UUID jobId, String owner, long leaseMillis) {
    List<Map<String, Object>> rows =
        jdbc.queryForList("SELECT lease_generation FROM jobs WHERE id=? FOR UPDATE", jobId);
    if (rows.isEmpty()) throw new NotFoundException("job not found");
    long gen = ((Number) rows.get(0).get("lease_generation")).longValue() + 1;
    // Count attempts so far to enforce bound.
    Long n =
        jdbc.queryForObject("SELECT count(*) FROM attempts WHERE job_id = ?", Long.class, jobId);
    if (n != null && n >= maxAttempts) {
      jdbc.update("UPDATE jobs SET status='DEAD_LETTER', updated_at=now() WHERE id=?", jobId);
      return null;
    }
    jdbc.update(
        "UPDATE jobs SET status='LEASED', lease_owner=?, lease_expiry=now() + CAST(? AS INTEGER) * INTERVAL '1 millisecond',"
            + " lease_generation=?, updated_at=now() WHERE id=?",
        owner, (int) leaseMillis, gen, jobId);
    // An attempt still STARTED at this point belonged to a worker that died before
    // reporting any outcome (crash, SIGKILL, halt). Close it as ABANDONED so the
    // attempt trail never dangles between generations.
    jdbc.update(
        "UPDATE attempts SET outcome='ABANDONED', finished_at=now() WHERE job_id=? AND outcome='STARTED'",
        jobId);
    int attemptNo = (n == null ? 0 : n.intValue()) + 1;
    jdbc.update(
        "INSERT INTO attempts(job_id, attempt_no, owner, generation, outcome) VALUES (?,?,?,?,'STARTED')",
        jobId, attemptNo, owner, gen);
    var job = jdbc.queryForMap("SELECT * FROM jobs WHERE id=?", jobId);
    return job;
  }

  /**
   * Complete a leased job. Generation must match current generation, else STALE rejection.
   * Commits results + outbox event in ONE transaction.
   */
  @Transactional
  public void completeWithGeneration(
      UUID jobId, String owner, long generation, String dedupKey, String output) {
    Long current =
        jdbc.queryForObject(
            "SELECT lease_generation FROM jobs WHERE id=?", Long.class, jobId);
    if (current == null) throw new NotFoundException("job not found");
    if (current != generation) {
      jdbc.update(
          "UPDATE attempts SET outcome='STALE', finished_at=now() WHERE job_id=? AND generation=? AND outcome='STARTED'",
          jobId, generation);
      throw new StaleLeaseException(
          "stale generation: presented " + generation + " current " + current);
    }
    jdbc.update(
        "INSERT INTO results(job_id, output) VALUES (?,CAST(? AS jsonb)) ON CONFLICT (job_id) DO NOTHING",
        jobId, output);
    jdbc.update(
        "INSERT INTO outbox_events(id, job_id, type, payload) VALUES (?,?,?,CAST(? AS jsonb)) ON CONFLICT DO NOTHING",
        UUID.randomUUID(), jobId, "job.completed", "{\"jobId\":\"" + jobId + "\"}");
    jdbc.update(
        "UPDATE jobs SET status='SUCCEEDED', result=CAST(? AS jsonb), updated_at=now() WHERE id=? AND lease_generation=?",
        output, jobId, generation);
    jdbc.update(
        "UPDATE attempts SET outcome='SUCCEEDED', finished_at=now() WHERE job_id=? AND generation=? AND outcome='STARTED'",
        jobId, generation);
  }

  @Transactional
  public void failAttempt(UUID jobId, long generation, String reason) {
    jdbc.update(
        "UPDATE attempts SET outcome=?, finished_at=now() WHERE job_id=? AND generation=? AND outcome='STARTED'",
        "FAILED:" + reason, jobId, generation);
    // Release lease so another worker can retry (generation will bump on next lease).
    jdbc.update(
        "UPDATE jobs SET status='FAILED', lease_expiry=now()-interval '1 second', updated_at=now() WHERE id=?",
        jobId);
  }

  public MockDownstream downstream() {
    return downstream;
  }

  public static class ConflictException extends RuntimeException {
    public ConflictException(String m) {
      super(m);
    }
  }

  public static class ValidationException extends RuntimeException {
    public ValidationException(String m) {
      super(m);
    }
  }

  public static class NotFoundException extends RuntimeException {
    public NotFoundException(String m) {
      super(m);
    }
  }

  public static class StaleLeaseException extends RuntimeException {
    public StaleLeaseException(String m) {
      super(m);
    }
  }
}
