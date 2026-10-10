package queue;

import com.sun.net.httpserver.*;
import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.*;

/** Minimal JSON REST over JDK HttpServer. Identity = X-User header (demo auth). */
public class Server {
    private final Db db;

    public Server(Db db) { this.db = db; }

    static String esc(String s) {
        return s.replace("\\", "\\\\").replace("\"", "\\\"");
    }

    static String itemJson(Db.Item i) {
        return "{\"id\":" + i.id() + ",\"owner\":\"" + esc(i.owner()) + "\",\"title\":\""
            + esc(i.title()) + "\",\"url\":\"" + esc(i.url()) + "\",\"status\":\"" + i.status() + "\"}";
    }

    static Map<String, String> query(String raw) {
        Map<String, String> m = new HashMap<>();
        if (raw == null) return m;
        for (String kv : raw.split("&")) {
            String[] p = kv.split("=", 2);
            if (p.length == 2) m.put(p[0], URLDecoder.decode(p[1], StandardCharsets.UTF_8));
        }
        return m;
    }

    static String readBody(HttpExchange ex) throws IOException {
        return new String(ex.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
    }

    static String field(String json, String name) {
        var m = java.util.regex.Pattern.compile("\"" + name + "\"\\s*:\\s*\"([^\"]*)\"").matcher(json);
        return m.find() ? m.group(1) : "";
    }

    void send(HttpExchange ex, int code, String body) throws IOException {
        byte[] b = body.getBytes(StandardCharsets.UTF_8);
        ex.getResponseHeaders().set("Content-Type", "application/json");
        ex.sendResponseHeaders(code, b.length);
        try (OutputStream o = ex.getResponseBody()) { o.write(b); }
    }

    int statusEx(Exception e) {
        if (e instanceof Db.NotFound) return 404;
        if (e instanceof Db.Forbidden) return 403;
        return 400;
    }

    public HttpServer start(int port) throws IOException {
        HttpServer s = HttpServer.create(new InetSocketAddress("127.0.0.1", port), 0);
        s.createContext("/api/items", ex -> {
            try {
                String user = Optional.ofNullable(ex.getRequestHeaders().getFirst("X-User")).orElse("anon");
                String method = ex.getRequestMethod();
                String[] p = ex.getRequestURI().getPath().split("/");
                // /api/items  |  /api/items/{id}  |  /api/items/{id}/transfer
                if (p.length == 3 && method.equals("GET")) {
                    var q = query(ex.getRequestURI().getRawQuery());
                    int page = Integer.parseInt(q.getOrDefault("page", "1"));
                    int per = Integer.parseInt(q.getOrDefault("per_page", "10"));
                    var pg = db.list(q.getOrDefault("search", ""), page, per);
                    StringBuilder sb = new StringBuilder("{\"items\":[");
                    for (int i = 0; i < pg.items().size(); i++) {
                        if (i > 0) sb.append(",");
                        sb.append(itemJson(pg.items().get(i)));
                    }
                    sb.append("],\"page\":").append(pg.page()).append(",\"per_page\":")
                      .append(pg.perPage()).append(",\"total\":").append(pg.total()).append("}");
                    send(ex, 200, sb.toString());
                } else if (p.length == 3 && method.equals("POST")) {
                    String body = readBody(ex);
                    var it = db.create(user, field(body, "title"), field(body, "url"));
                    send(ex, 201, itemJson(it));
                } else if (p.length == 4 && !"transfer".equals(p[3])) {
                    long id = Long.parseLong(p[3]);
                    if (method.equals("GET")) {
                        var it = db.get(id);
                        send(ex, it.isPresent() ? 200 : 404,
                             it.map(Server::itemJson).orElse("{\"error\":\"not found\"}"));
                    } else if (method.equals("PATCH")) {
                        var it = db.setStatus(user, id, field(readBody(ex), "status"));
                        send(ex, 200, itemJson(it));
                    } else if (method.equals("DELETE")) {
                        db.delete(user, id);
                        send(ex, 200, "{\"ok\":true}");
                    } else send(ex, 405, "{\"error\":\"method\"}");
                } else if (p.length == 5 && "transfer".equals(p[4]) && method.equals("POST")) {
                    var it = db.transfer(user, Long.parseLong(p[3]), field(readBody(ex), "to"), null);
                    send(ex, 200, itemJson(it));
                } else send(ex, 404, "{\"error\":\"not found\"}");
            } catch (Exception e) {
                try { send(ex, statusEx(e), "{\"error\":\"" + esc(String.valueOf(e.getMessage())) + "\"}"); }
                catch (IOException ignored) {}
            }
        });
        s.start();
        return s;
    }

    public static void main(String[] args) throws Exception {
        String url = System.getenv().getOrDefault("JDBC_URL", "jdbc:postgresql://127.0.0.1:55433/readingqueue");
        int port = args.length > 0 ? Integer.parseInt(args[0]) : 8581;
        Db db = Databases.connect(url);
        db.migrate(Path.of(Databases.migrations(url)));
        new Server(db).start(port);
        System.out.println("readingqueue on " + port);
    }
}
