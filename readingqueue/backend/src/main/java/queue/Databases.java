package queue;
/** Select an actual JDBC dialect, never emulate SQL Server with PostgreSQL. */
public final class Databases {
    public static Db connect(String url) {
        return url.startsWith("jdbc:sqlserver:") ? new SqlServerDb(url) : new PostgresDb(url);
    }
    public static String migrations(String url) {
        return url.startsWith("jdbc:sqlserver:") ? "../db/sqlserver" : "../db/postgres";
    }
}
