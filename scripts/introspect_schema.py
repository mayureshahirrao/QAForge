
import json
import psycopg2
import pymysql
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "test_data" / "static"


def fetch_postgres_schema():
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        user="postgres",
        password="Admin@123",
        database="dvdrental",
    )
    cur = conn.cursor()

    cur.execute("""
        SELECT table_name, column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position
    """)
    columns_rows = cur.fetchall()

    cur.execute("""
        SELECT
            kcu.table_name,
            kcu.column_name,
            ccu.table_name  AS foreign_table,
            ccu.column_name AS foreign_column
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema   = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema   = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema    = 'public'
    """)
    fk_rows = cur.fetchall()
    conn.close()

    fk_map: dict[tuple, dict] = {}
    for table, column, fk_table, fk_column in fk_rows:
        fk_map[(table, column)] = {"table": fk_table, "column": fk_column}

    schema: dict[str, list] = {}
    for table, column, data_type, is_nullable in columns_rows:
        schema.setdefault(table, []).append({
            "column": column,
            "type": data_type,
            "nullable": is_nullable == "YES",
            "fk": fk_map.get((table, column)),
        })
    return schema


def fetch_mysql_schema():
    conn = pymysql.connect(
        host="localhost",
        port=3306,
        user="root",
        password="Admin@123",
        db="world",
        charset="utf8",
    )
    cur = conn.cursor()

    cur.execute("""
        SELECT table_name, column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'world'
        ORDER BY table_name, ordinal_position
    """)
    columns_rows = cur.fetchall()

    cur.execute("""
        SELECT
            kcu.table_name,
            kcu.column_name,
            kcu.referenced_table_name,
            kcu.referenced_column_name
        FROM information_schema.key_column_usage AS kcu
        JOIN information_schema.table_constraints AS tc
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema   = kcu.table_schema
            AND tc.table_name     = kcu.table_name
        WHERE tc.constraint_type       = 'FOREIGN KEY'
          AND kcu.table_schema         = 'world'
          AND kcu.referenced_table_name IS NOT NULL
    """)
    fk_rows = cur.fetchall()
    conn.close()

    fk_map: dict[tuple, dict] = {}
    for table, column, fk_table, fk_column in fk_rows:
        fk_map[(table, column)] = {"table": fk_table, "column": fk_column}

    schema: dict[str, list] = {}
    for table, column, data_type, is_nullable in columns_rows:
        schema.setdefault(table, []).append({
            "column": column,
            "type": data_type,
            "nullable": is_nullable == "YES",
            "fk": fk_map.get((table, column)),
        })
    return schema


def save(schema: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    print(f"Saved {len(schema)} tables -> {path}")


if __name__ == "__main__":
    print("Introspecting PostgreSQL (dvdrental)…")
    pg_schema = fetch_postgres_schema()
    save(pg_schema, OUTPUT_DIR / "schema_snapshot_postgres.json")

    print("Introspecting MySQL (world)…")
    my_schema = fetch_mysql_schema()
    save(my_schema, OUTPUT_DIR / "schema_snapshot_mysql.json")

    print("Done.")