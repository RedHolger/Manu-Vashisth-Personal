package queue;

import java.util.List;
import java.util.Optional;

/** Reading-list store. T-SQL twin implements the same contract (UNRUN). */
public interface Db {
    record Item(long id, String owner, String title, String url, String status) {}
    record Page(List<Item> items, int page, int perPage, long total) {}

    void migrate(java.nio.file.Path migrationsDir) throws Exception;
    Page list(String search, int page, int perPage) throws Exception;
    Optional<Item> get(long id) throws Exception;
    Item create(String owner, String title, String url) throws Exception;
    Item setStatus(String user, long id, String status) throws Exception;
    void delete(String user, long id) throws Exception;
    /** Transactional ownership transfer. Hook runs after UPDATE (test seam). */
    Item transfer(String user, long id, String to, Runnable afterUpdate) throws Exception;

    class NotFound extends Exception { NotFound(String m) { super(m); } }
    class Forbidden extends Exception { Forbidden(String m) { super(m); } }
    class BadRequest extends Exception { BadRequest(String m) { super(m); } }
}
