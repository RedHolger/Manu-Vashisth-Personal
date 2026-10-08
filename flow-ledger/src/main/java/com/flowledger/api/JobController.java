package com.flowledger.api;

import com.flowledger.service.JobService;
import java.util.Map;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
public class JobController {
  private final JobService jobs;

  public JobController(JobService jobs) {
    this.jobs = jobs;
  }

  @GetMapping("/health")
  public Map<String, String> health() {
    return Map.of("status", "OK");
  }

  @PostMapping("/jobs")
  public ResponseEntity<?> submit(
      @RequestHeader(value = "Idempotency-Key", required = false) String key,
      @RequestBody Map<String, Object> body) {
    if (key == null || key.isBlank()) {
      return ResponseEntity.badRequest().body(Map.of("error", "Idempotency-Key required"));
    }
    String type = (String) body.getOrDefault("type", "echo");
    String payload;
    try {
      payload =
          new com.fasterxml.jackson.databind.ObjectMapper().writeValueAsString(body.getOrDefault("payload", Map.of()));
    } catch (Exception e) {
      payload = "{}";
    }
    try {
      var r = jobs.submit(key, type, payload);
      return ResponseEntity.status(r.created() ? 201 : 200)
          .body(Map.of("jobId", r.jobId().toString(), "status", r.status(), "created", r.created()));
    } catch (JobService.ValidationException v) {
      return ResponseEntity.badRequest().body(Map.of("error", v.getMessage()));
    } catch (JobService.ConflictException c) {
      return ResponseEntity.status(HttpStatus.CONFLICT).body(Map.of("error", c.getMessage()));
    }
  }

  @GetMapping("/jobs/{id}")
  public ResponseEntity<?> get(@PathVariable String id) {
    try {
      var job = jobs.get(UUID.fromString(id));
      return ResponseEntity.ok(
          Map.of(
              "jobId", job.get("id").toString(),
              "status", job.get("status"),
              "result", String.valueOf(job.get("result")),
              "attempts", job.get("attempts"),
              "leaseGeneration", job.get("lease_generation")));
    } catch (JobService.NotFoundException n) {
      return ResponseEntity.status(404).body(Map.of("error", "not found"));
    }
  }
}
