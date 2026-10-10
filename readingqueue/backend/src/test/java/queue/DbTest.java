package queue;

import org.junit.jupiter.api.*;
import java.nio.file.Path;
import static org.junit.jupiter.api.Assertions.*;

@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
public class DbTest {
    static Db db;
    static String URL = System.getenv().getOrDefault("JDBC_URL", System.getProperty("jdbcUrl", "jdbc:postgresql://127.0.0.1:55433/readingqueue"));

    @BeforeAll
    static void migrate() throws Exception {
        db = Databases.connect(URL);
        db.migrate(Path.of(System.getProperty("migrations", Databases.migrations(URL))));
        try (var c = java.sql.DriverManager.getConnection(URL);
             var s = c.createStatement()) {
            // DELETE works on both PostgreSQL and SQL Server (TRUNCATE items is PG-only syntax).
            s.execute("DELETE FROM items");
        }
    }

    @Test @Order(1)
    void migrationOrderAndIdempotence() throws Exception {
        // second run must be a no-op (idempotent)
        db.migrate(Path.of(System.getProperty("migrations", Databases.migrations(URL))));
        try (var c = java.sql.DriverManager.getConnection(URL);
             var rs = c.createStatement().executeQuery(
                 "SELECT name FROM schema_migrations ORDER BY name")) {
            assertEquals("V1__init.sql", rs.next() ? rs.getString(1) : null);
            assertEquals("V2__status.sql", rs.next() ? rs.getString(1) : null);
            assertFalse(rs.next());
        }
    }

    @Test @Order(2)
    void ownershipEnforced() throws Exception {
        var it = db.create("alice", "Valve handbook", "http://x");
        assertThrows(Db.Forbidden.class, () -> db.setStatus("bob", it.id(), "done"));
        assertThrows(Db.Forbidden.class, () -> db.delete("bob", it.id()));
        assertEquals("reading", db.setStatus("alice", it.id(), "reading").status());
        assertThrows(Db.NotFound.class, () -> db.setStatus("alice", 999999, "done"));
    }

    @Test @Order(3)
    void searchAndPagination() throws Exception {
        db.create("alice", "Pump curves", "http://x");
        db.create("alice", "Pump seals", "http://x");
        var pg = db.list("PUMP", 1, 50);
        assertTrue(pg.total() >= 2);
        assertTrue(pg.items().stream().allMatch(i -> i.title().toLowerCase().contains("pump")));
        var capped = db.list("", 1, 500);
        assertEquals(50, capped.perPage());
        var empty = db.list("", 999, 10);
        assertTrue(empty.items().isEmpty());
    }

    @Test @Order(4)
    void transferCommits() throws Exception {
        var it = db.create("alice", "Giveaway", "http://x");
        var moved = db.transfer("alice", it.id(), "bob", null);
        assertEquals("bob", moved.owner());
        assertEquals("bob", db.get(it.id()).orElseThrow().owner());
    }

    @Test @Order(5)
    void transferRollsBackOnMidTxnFailure() throws Exception {
        var it = db.create("alice", "Atomic", "http://x");
        RuntimeException boom = assertThrows(RuntimeException.class, () ->
            db.transfer("alice", it.id(), "bob", () -> { throw new RuntimeException("hook"); }));
        assertEquals("hook", boom.getMessage());
        assertEquals("alice", db.get(it.id()).orElseThrow().owner()); // unchanged
    }

    @Test @Order(6)
    void validation() throws Exception {
        assertThrows(Db.BadRequest.class, () -> db.create("alice", "  ", "http://x"));
        var it = db.create("alice", "V", "http://x");
        assertThrows(Db.BadRequest.class, () -> db.setStatus("alice", it.id(), "lost"));
        assertThrows(Db.BadRequest.class, () -> db.transfer("alice", it.id(), " ", null));
    }
}
