import re
import sqlite3

DB_PATH = "movies.db"

ALLOWED_TABLES = {"movies"}
ALLOWED_COLUMNS = {
    "name", "rating", "genre", "year", "score", "votes",
    "director", "writer", "star", "country", "budget",
    "gross", "company", "runtime"
}

BANNED_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "TRUNCATE", "REPLACE", "ATTACH", "DETACH", "PRAGMA", "VACUUM"
}


class SQLValidationError(Exception):
    """Raised when generated SQL fails a safety check."""
    pass


def validate_sql(sql: str) -> None:
    """
    Raises SQLValidationError if the SQL fails any safety check.
    Does nothing (returns None) if the SQL passes.
    """
    sql_stripped = sql.strip().rstrip(";")

    # 1. Must start with SELECT
    if not sql_stripped.upper().startswith("SELECT"):
        raise SQLValidationError(f"Only SELECT statements are allowed. Got: {sql_stripped[:50]}")

    # 2. Must not contain banned keywords anywhere (as whole words)
    tokens = set(re.findall(r"[A-Za-z_]+", sql_stripped.upper()))
    banned_found = tokens & BANNED_KEYWORDS
    if banned_found:
        raise SQLValidationError(f"Banned keyword(s) found: {banned_found}")

    # 3. Must not reference multiple statements (basic guard against "SELECT ...; DROP ...")
    if ";" in sql.strip().rstrip(";"):
        raise SQLValidationError("Multiple statements are not allowed.")

    # 4. Table name check — must reference only allowed tables
    # (simple heuristic: look for "FROM <word>" and "JOIN <word>")
    referenced_tables = set(re.findall(r"(?:FROM|JOIN)\s+([A-Za-z_]+)", sql_stripped, re.IGNORECASE))
    referenced_tables = {t.lower() for t in referenced_tables}
    unknown_tables = referenced_tables - ALLOWED_TABLES
    if unknown_tables:
        raise SQLValidationError(f"Unknown table(s) referenced: {unknown_tables}")


def execute_sql(sql: str) -> tuple[list[str], list[tuple]]:
    """
    Validates and executes SQL against movies.db in read-only mode.
    Returns (column_names, rows).
    Raises SQLValidationError or sqlite3.Error on failure.
    """
    validate_sql(sql)

    # Open in read-only mode as a second safety layer beyond the validator
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return columns, rows
    finally:
        conn.close()


# ---- Quick manual test ----
if __name__ == "__main__":
    test_cases = [
        "SELECT name, votes FROM movies ORDER BY votes DESC LIMIT 5;",
        "SELECT genre, AVG(runtime) AS avg_runtime FROM movies GROUP BY genre;",
        "DELETE FROM movies WHERE genre = 'Action';",   # should be rejected
        "SELECT * FROM users;",                          # should be rejected (unknown table)
    ]

    for sql in test_cases:
        print(f"SQL: {sql}")
        try:
            columns, rows = execute_sql(sql)
            print(f"  Columns: {columns}")
            print(f"  Rows returned: {len(rows)}")
            print(f"  Sample: {rows[:2]}")
        except SQLValidationError as e:
            print(f"  REJECTED: {e}")
        except sqlite3.Error as e:
            print(f"  DB ERROR: {e}")
        print()