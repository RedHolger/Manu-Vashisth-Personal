package com.flowledger;

import static org.junit.jupiter.api.Assertions.*;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.flowledger.service.JobService;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.Callable;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;

/**
 * Gate P04-02: HTTP API and database contract. Env: real PostgreSQL on RANDOM_PORT,
 * worker/relay disabled. Assertions: POST /jobs is 201 on create and 200 on idempotent
 * replay with one jobId, 409 on same key with a different body, 400 on missing key or
 * unsupported type; GET /jobs/{id} is 200 for an existing job and 404 otherwise; concurrent
 * mixed-payload submissions yield exactly one job or an explicit conflict and leave no
 * partial child rows.
 */
@SpringBootTest(
    webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
    properties = {"flowledger.worker.enabled=false", "flowledger.relay.enabled=false"})
public class ApiContractTest {
  @Autowired JobService jobs;
  @Autowired JdbcTemplate jdbc;
  @Autowired TestRestTemplate http;
  final ObjectMapper json = new ObjectMapper();

  @BeforeEach
  void clean() {
    jdbc.update("DELETE FROM consumer_seen");
    jdbc.update("DELETE FROM outbox_events");
    jdbc.update("DELETE FROM results");
    jdbc.update("DELETE FROM attempts");
    jdbc.update("DELETE FROM downstream_effects");
    jdbc.update("DELETE FROM jobs");
  }

  HttpHeaders headers(String key) {
    HttpHeaders h = new HttpHeaders();
    h.setContentType(MediaType.APPLICATION_JSON);
    if (key != null) h.set("Idempotency-Key", key);
    return h;
  }

  ResponseEntity<String> post(String key, Map<String, Object> body) {
    return http.postForEntity("/jobs", new HttpEntity<>(body, headers(key)), String.class);
  }

  Map<String, Object> body(String type, Map<String, Object> payload) {
    return Map.of("type", type, "payload", payload);
  }

  @Test
  void postCreatesThenReplaysWithOneJobId() {
    String key = "key-" + UUID.randomUUID();
    var first = post(key, body("echo", Map.of("a", 1)));
    assertEquals(HttpStatus.CREATED, first.getStatusCode());
    Map<?, ?> created = read(first);
    assertEquals(true, created.get("created"));

    var second = post(key, body("echo", Map.of("a", 1)));
    assertEquals(HttpStatus.OK, second.getStatusCode());
    Map<?, ?> replay = read(second);
    assertEquals(created.get("jobId"), replay.get("jobId"));
    assertEquals(false, replay.get("created"));
    assertEquals(
        1L, jdbc.queryForObject("SELECT count(*) FROM jobs WHERE idempotency_key=?", Long.class, key));
  }

  @Test
  void postSameKeyDifferentBodyConflicts() {
    String key = "key-" + UUID.randomUUID();
    assertEquals(HttpStatus.CREATED, post(key, body("echo", Map.of("a", 1))).getStatusCode());
    var conflict = post(key, body("echo", Map.of("a", 2)));
    assertEquals(HttpStatus.CONFLICT, conflict.getStatusCode());
    assertNotNull(read(conflict).get("error"));
    assertEquals(
        1L, jdbc.queryForObject("SELECT count(*) FROM jobs WHERE idempotency_key=?", Long.class, key));
  }

  @Test
  void postRejectsMissingKeyAndUnsupportedType() {
    assertEquals(HttpStatus.BAD_REQUEST, post(null, body("echo", Map.of())).getStatusCode());
    assertEquals(
        HttpStatus.BAD_REQUEST, post("key-" + UUID.randomUUID(), body("nope", Map.of())).getStatusCode());
    assertEquals(
        0L, jdbc.queryForObject("SELECT count(*) FROM jobs", Long.class), "invalid requests write nothing");
  }

  @Test
  void getReturnsJobOr404() {
    var r = post("key-" + UUID.randomUUID(), body("echo", Map.of("a", 1)));
    String id = (String) read(r).get("jobId");

    var ok = http.getForEntity("/jobs/" + id, String.class);
    assertEquals(HttpStatus.OK, ok.getStatusCode());
    Map<?, ?> job = read(ok);
    assertEquals(id, job.get("jobId"));
    assertEquals("PENDING", job.get("status"));
    assertEquals(0, ((Number) job.get("attempts")).intValue());

    var missing = http.getForEntity("/jobs/" + UUID.randomUUID(), String.class);
    assertEquals(HttpStatus.NOT_FOUND, missing.getStatusCode());
  }

  @Test
  void concurrentMixedPayloadsYieldOneJobOrConflictNoPartialState() throws Exception {
    String key = "key-" + UUID.randomUUID();
    int threads = 8;
    var pool = Executors.newFixedThreadPool(threads);
    List<Callable<String>> tasks = new ArrayList<>();
    for (int i = 0; i < threads; i++) {
      int variant = i % 2;
      tasks.add(
          () -> {
            var res = post(key, body("echo", Map.of("order", variant)));
            HttpStatus s = (HttpStatus) res.getStatusCode();
            if (s == HttpStatus.CONFLICT) return "CONFLICT";
            if (s == HttpStatus.CREATED || s == HttpStatus.OK) return "OK:" + read(res).get("jobId");
            return "UNEXPECTED:" + s + ":" + res.getBody();
          });
    }
    var results = pool.invokeAll(tasks);
    pool.shutdown();
    assertTrue(pool.awaitTermination(60, TimeUnit.SECONDS));

    String winner = null;
    int ok = 0, conflict = 0;
    for (var f : results) {
      String out = f.get(10, TimeUnit.SECONDS);
      assertTrue(out.startsWith("OK:") || out.equals("CONFLICT"), "unexpected response: " + out);
      if (out.equals("CONFLICT")) {
        conflict++;
      } else {
        ok++;
        String id = out.substring(3);
        if (winner == null) winner = id;
        assertEquals(winner, id, "every non-conflict response must return the same job");
      }
    }
    assertTrue(ok >= 1, "one payload family must win");
    assertTrue(conflict >= 1, "the losing family must see an explicit 409");

    assertEquals(
        1L, jdbc.queryForObject("SELECT count(*) FROM jobs WHERE idempotency_key=?", Long.class, key));
    assertEquals(1L, jdbc.queryForObject("SELECT count(*) FROM jobs", Long.class));
    assertEquals(0L, jdbc.queryForObject("SELECT count(*) FROM attempts", Long.class));
    assertEquals(0L, jdbc.queryForObject("SELECT count(*) FROM results", Long.class));
    assertEquals(0L, jdbc.queryForObject("SELECT count(*) FROM outbox_events", Long.class));
    assertEquals(0L, jdbc.queryForObject("SELECT count(*) FROM downstream_effects", Long.class));
  }

  @SuppressWarnings("unchecked")
  Map<String, Object> read(ResponseEntity<String> res) {
    try {
      return json.readValue(res.getBody(), Map.class);
    } catch (Exception e) {
      throw new AssertionError("unreadable body: " + res.getBody(), e);
    }
  }

  @Test
  void headOfLineExhaustedJobIsRetiredAndQueueAdvances() {
    // Job A exhausts its five attempts with expired leases (crashed worker, no failAttempt).
    var a = jobs.submit("key-" + UUID.randomUUID(), "echo", "{}");
    for (int i = 0; i < 5; i++) {
      assertNotNull(jobs.leaseJob(a.jobId(), "crashy-" + i, 10000), "attempt " + i);
      jdbc.update(
          "UPDATE jobs SET lease_expiry = now() - interval '1 second' WHERE id = ?", a.jobId());
    }
    // A is older than B, so it is the head of the oldest-eligible ordering.
    jdbc.update("UPDATE jobs SET created_at = now() - interval '1 minute' WHERE id = ?", a.jobId());
    var b = jobs.submit("key-" + UUID.randomUUID(), "echo", "{}");

    var leased = jobs.leaseNext("worker", 10000);
    assertNotNull(leased, "an exhausted head-of-line job must not block the queue");
    assertEquals(b.jobId(), leased.get("id"), "the eligible job must be leased");
    assertEquals("DEAD_LETTER", jobs.get(a.jobId()).get("status"), "the exhausted job is retired");
    assertEquals(
        5L,
        jdbc.queryForObject(
            "SELECT count(*) FROM attempts WHERE job_id = ?", Long.class, a.jobId()),
        "retirement must not add a sixth attempt");
  }
}
