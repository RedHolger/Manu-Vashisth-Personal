package queue;

import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.*;
import java.net.URI;
import java.net.http.*;
import java.nio.file.Path;
import static org.junit.jupiter.api.Assertions.*;

public class ApiTest {
    static String URL = System.getenv().getOrDefault("JDBC_URL", System.getProperty("jdbcUrl", "jdbc:postgresql://127.0.0.1:55433/readingqueue"));
    static int PORT;
    static final HttpClient HTTP = HttpClient.newHttpClient();

        static String[] call(String method, String path, String user) throws Exception {
        return call(method, path, user, null);
    }

    static String[] call(String method, String path, String user, String body) throws Exception {        var b = HttpRequest.newBuilder(URI.create("http://127.0.0.1:" + PORT + path));
        if (user != null) b.header("X-User", user);
        b.header("Content-Type", "application/json");
        b.method(method, body == null
            ? HttpRequest.BodyPublishers.noBody()
            : HttpRequest.BodyPublishers.ofString(body));
        var r = HTTP.send(b.build(), HttpResponse.BodyHandlers.ofString());
        return new String[]{String.valueOf(r.statusCode()), r.body()};
    }

    @BeforeAll
    static void start() throws Exception {
        var db = Databases.connect(URL);
        db.migrate(Path.of(System.getProperty("migrations", Databases.migrations(URL))));
        try (var c = java.sql.DriverManager.getConnection(URL);
             var s = c.createStatement()) {
            // DELETE works on both PostgreSQL and SQL Server (TRUNCATE items is PG-only syntax).
            s.execute("DELETE FROM items");
        }
        HttpServer s = new Server(db).start(0);
        PORT = s.getAddress().getPort();
    }

    @Test
    void crudRoundTrip() throws Exception {
        var post = call("POST", "/api/items", "alice", "{\"title\":\"T\",\"url\":\"http://x\"}");
        assertEquals("201", post[0]);
        var get = call("GET", "/api/items?search=t", "alice");
        assertEquals("200", get[0]);
        assertTrue(get[1].contains("\"title\":\"T\""));
    }

    @Test
    void httpOwnership() throws Exception {
        var created = call("POST", "/api/items", "alice", "{\"title\":\"Mine\",\"url\":\"\"}");
        long id = Long.parseLong(created[1].replaceAll(".*\"id\":(\\d+).*", "$1"));
        var r = call("PATCH", "/api/items/" + id, "bob", "{\"status\":\"done\"}");
        assertEquals("403", r[0]);
        var d = call("DELETE", "/api/items/" + id, "bob", null);
        assertEquals("403", d[0]);
        var ok = call("PATCH", "/api/items/" + id, "alice", "{\"status\":\"done\"}");
        assertEquals("200", ok[0]);
    }

    @Test
    void codes() throws Exception {
        assertEquals("404", call("GET", "/api/items/999999", "alice")[0]);
        var bad = call("POST", "/api/items", "alice", "{\"title\":\"\",\"url\":\"\"}");
        assertEquals("400", bad[0]);
        var per = call("GET", "/api/items?per_page=500", "alice");
        assertTrue(per[1].contains("\"per_page\":50"));
    }
}
