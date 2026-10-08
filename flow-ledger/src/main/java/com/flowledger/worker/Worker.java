package com.flowledger.worker;

import com.flowledger.service.JobService;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
@ConditionalOnProperty(name = "flowledger.worker.enabled", havingValue = "true", matchIfMissing = true)
public class Worker {
  private static final Logger log = LoggerFactory.getLogger(Worker.class);
  private final JobService jobs;
  private final long leaseMillis;
  private final boolean haltAfterEffect;
  private final long sleepAfterEffectMs;
  private final String owner = "worker-" + UUID.randomUUID().toString().substring(0, 8);

  public Worker(JobService jobs,
      @Value("${flowledger.worker.leaseMillis:10000}") long leaseMillis,
      @Value("${flowledger.fault.halt-after-effect:false}") boolean haltAfterEffect,
      @Value("${flowledger.fault.sleep-after-effect-ms:0}") long sleepAfterEffectMs) {
    this.jobs = jobs;
    this.leaseMillis = leaseMillis;
    this.haltAfterEffect = haltAfterEffect;
    this.sleepAfterEffectMs = sleepAfterEffectMs;
  }

  /** halt() runs no shutdown hooks and flushes nothing — push the record out first. */
  static void flushLogs() {
    System.out.flush();
    System.err.flush();
  }

  @Scheduled(fixedDelay = 500)
  public void tick() {
    var job = jobs.leaseNext(owner, leaseMillis);
    if (job == null) return;
    UUID jobId = (UUID) job.get("id");
    long gen = ((Number) job.get("lease_generation")).longValue();
    String payload = String.valueOf(job.get("payload"));
    String dedupKey = jobId + ":op-1"; // stable per logical operation
    try {
      var effect = jobs.downstream().execute(dedupKey, jobId, payload);
      if (haltAfterEffect) {
        // fault: process dies after the downstream effect committed but before the
        // local completion transaction, i.e. the effect-before-ack boundary.
        log.error(
            "fault halt-after-effect: killing process job={} gen={} dedup={}",
            jobId, gen, dedupKey);
        flushLogs();
        Runtime.getRuntime().halt(77);
      }
      if (sleepAfterEffectMs > 0) {
        // fault: hold this lease open past its expiry so a second live worker takes
        // over; when we resume, our generation must be fenced out.
        log.info(
            "fault sleep-after-effect-ms={} job={} gen={}", sleepAfterEffectMs, jobId, gen);
        try {
          Thread.sleep(sleepAfterEffectMs);
        } catch (InterruptedException e) {
          Thread.currentThread().interrupt();
          return;
        }
      }
      jobs.completeWithGeneration(jobId, owner, gen, dedupKey, effect.output());
    } catch (JobService.StaleLeaseException s) {
      log.info("stale commit rejected job={} gen={}", jobId, gen);
    } catch (Exception e) {
      log.info("attempt failed job={} gen={} err={}", jobId, gen, e.getMessage());
      try {
        jobs.failAttempt(jobId, gen, e.getMessage());
      } catch (Exception ignored) {
      }
    }
  }
}
