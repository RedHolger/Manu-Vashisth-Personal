package com.flowledger.service;

import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/** Relay: dispatches undispatched outbox events to a mock consumer with dedup. */
@Component
@ConditionalOnProperty(name = "flowledger.relay.enabled", havingValue = "true", matchIfMissing = true)
public class OutboxRelay {
  private static final Logger log = LoggerFactory.getLogger(OutboxRelay.class);
  private final JdbcTemplate jdbc;
  private final boolean haltAfterConsumerAccept;
  public volatile boolean killBeforeDispatch = false;

  public OutboxRelay(JdbcTemplate jdbc,
      @Value("${flowledger.fault.halt-after-consumer-accept:false}") boolean haltAfterConsumerAccept) {
    this.jdbc = jdbc;
    this.haltAfterConsumerAccept = haltAfterConsumerAccept;
  }

  @Scheduled(fixedDelay = 500)
  public void tick() {
    List<Map<String, Object>> rows =
        jdbc.queryForList(
            "SELECT id, job_id, payload FROM outbox_events WHERE dispatched=FALSE ORDER BY created_at LIMIT 10");
    for (var r : rows) {
      UUID eventId = (UUID) r.get("id");
      if (killBeforeDispatch) {
        // Simulate crash between commit and dispatch: skip this round.
        log.info("relay crash injected, skipping dispatch of {}", eventId);
        killBeforeDispatch = false;
        return;
      }
      try {
        jdbc.update("INSERT INTO consumer_seen(event_id) VALUES (?)", eventId);
      } catch (DuplicateKeyException dup) {
        // Already applied — just mark dispatched.
      }
      if (haltAfterConsumerAccept) {
        // fault: process dies after the consumer accepted the event but before the
        // outbox row is marked dispatched, i.e. the consumer-before-dispatch boundary.
        log.error(
            "fault halt-after-consumer-accept: killing process event={} job={}",
            eventId, r.get("job_id"));
        System.out.flush();
        System.err.flush();
        Runtime.getRuntime().halt(77);
      }
      jdbc.update("UPDATE outbox_events SET dispatched=TRUE WHERE id=?", eventId);
      log.info("dispatched {}", eventId);
    }
  }

  public long appliedCount() {
    Long n = jdbc.queryForObject("SELECT count(*) FROM consumer_seen", Long.class);
    return n == null ? 0 : n;
  }
}
