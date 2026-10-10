package queue;

import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.sql.*;
import java.util.*;

/** JDBC implementation, tested against local PostgreSQL 16. */
public class PostgresDb implements Db {
    private final String url;
    private static final Set<String> STATUSES = Set.of("unread", "reading", "done");

    public PostgresDb(String url) { this.url = url; }

    private Connection open() throws SQLException { return DriverManager.getConnection(url); }

    private static Item row(ResultSet r) throws SQLException {
        return new Item(r.getLong(1), r.getString(2), r.getString(3), r.getString(4), r.getString(5));
    }

    @Override
    public void migrate(Path dir) throws Exception {
        List<Path> files;
        try (var s = Files.list(dir)) {
            files = s.filter(p -> p.getFileName().toString().matches("V\\d+__.*\\.sql"))
                     .sorted().toList();
        }
        try (Connection c = open()) {
            c.createStatement().execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations(name TEXT PRIMARY KEY, sha TEXT)");
            for (Path f : files) {
                String name = f.getFileName().toString();
                var done = c.prepareStatement("SELECT 1 FROM schema_migrations WHERE name=?");
                done.setString(1, name);
                if (done.executeQuery().next()) continue;
                String sql = Files.readString(f);
                String sha = HexFormat.of().formatHex(
                    MessageDigest.getInstance("SHA-256").digest(sql.getBytes(StandardCharsets.UTF_8)));
                c.setAutoCommit(false);
                try {
                    for (String stmt : sql.split(";")) {
                        if (!stmt.isBlank()) c.createStatement().execute(stmt);
                    }
                    var ins = c.prepareStatement("INSERT INTO schema_migrations(name,sha) VALUES (?,?)");
                    ins.setString(1, name); ins.setString(2, sha); ins.executeUpdate();
                    c.commit();
                } catch (Exception e) { c.rollback(); throw e; }
                finally { c.setAutoCommit(true); }
            }
        }
    }

    @Override
    public Page list(String search, int page, int perPage) throws Exception {
        page = Math.max(1, page); perPage = Math.min(50, Math.max(1, perPage));
        String like = (search == null || search.isBlank()) ? "%" : "%" + search.toLowerCase() + "%";
        try (Connection c = open()) {
            var cnt = c.prepareStatement("SELECT COUNT(*) FROM items WHERE LOWER(title) LIKE ?");
            cnt.setString(1, like);
            var rc = cnt.executeQuery(); rc.next();
            long total = rc.getLong(1);
            var q = c.prepareStatement(
                "SELECT id,owner,title,url,status FROM items WHERE LOWER(title) LIKE ? ORDER BY id LIMIT ? OFFSET ?");
            q.setString(1, like); q.setInt(2, perPage); q.setInt(3, (page - 1) * perPage);
            List<Item> items = new ArrayList<>();
            var rs = q.executeQuery();
            while (rs.next()) items.add(row(rs));
            return new Page(items, page, perPage, total);
        }
    }

    @Override
    public Optional<Item> get(long id) throws Exception {
        try (Connection c = open()) {
            var q = c.prepareStatement("SELECT id,owner,title,url,status FROM items WHERE id=?");
            q.setLong(1, id);
            var rs = q.executeQuery();
            return rs.next() ? Optional.of(row(rs)) : Optional.empty();
        }
    }

    @Override
    public Item create(String owner, String title, String url) throws Exception {
        if (title == null || title.isBlank()) throw new BadRequest("title required");
        try (Connection c = open()) {
            var q = c.prepareStatement(
                "INSERT INTO items(owner,title,url) VALUES (?,?,?) RETURNING id,owner,title,url,status");
            q.setString(1, owner); q.setString(2, title); q.setString(3, url == null ? "" : url);
            var rs = q.executeQuery(); rs.next();
            return row(rs);
        }
    }

    private Item owned(String user, long id, Connection c) throws Exception {
        var q = c.prepareStatement("SELECT id,owner,title,url,status FROM items WHERE id=?");
        q.setLong(1, id);
        var rs = q.executeQuery();
        if (!rs.next()) throw new NotFound("item " + id);
        Item it = row(rs);
        if (!it.owner().equals(user)) throw new Forbidden("not your item");
        return it;
    }

    @Override
    public Item setStatus(String user, long id, String status) throws Exception {
        if (!STATUSES.contains(status)) throw new BadRequest("bad status");
        try (Connection c = open()) {
            owned(user, id, c);
            var q = c.prepareStatement(
                "UPDATE items SET status=? WHERE id=? RETURNING id,owner,title,url,status");
            q.setString(1, status); q.setLong(2, id);
            var rs = q.executeQuery(); rs.next();
            return row(rs);
        }
    }

    @Override
    public void delete(String user, long id) throws Exception {
        try (Connection c = open()) {
            owned(user, id, c);
            var q = c.prepareStatement("DELETE FROM items WHERE id=?");
            q.setLong(1, id); q.executeUpdate();
        }
    }

    @Override
    public Item transfer(String user, long id, String to, Runnable afterUpdate) throws Exception {
        if (to == null || to.isBlank()) throw new BadRequest("target owner required");
        try (Connection c = open()) {
            c.setAutoCommit(false);
            try {
                var lock = c.prepareStatement("SELECT id FROM items WHERE id=? FOR UPDATE");
                lock.setLong(1, id); lock.executeQuery();
                Item it = owned(user, id, c);
                var q = c.prepareStatement(
                    "UPDATE items SET owner=? WHERE id=? RETURNING id,owner,title,url,status");
                q.setString(1, to); q.setLong(2, id);
                var rs = q.executeQuery(); rs.next();
                Item moved = row(rs);
                if (afterUpdate != null) afterUpdate.run();
                c.commit();
                return moved;
            } catch (Exception e) { c.rollback(); throw e; }
            finally { c.setAutoCommit(true); }
        }
    }
}
