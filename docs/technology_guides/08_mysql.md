# 08 — Database Testing: MySQL

> **Source files:** `src/qaforge/database/mysql/client.py`, `features/steps/db_steps.py`, `features/database/persistence.feature`.

---

## 1. Driver choice

QAForge uses **PyMySQL** — pure-Python, easy to install (no native build), good enough for test workloads. For high-throughput production, you'd prefer `mysqlclient` (C extension), but it's overkill in CI.

---

## 2. Architecture

```
MySQLClient(cfg)
   ├─ connect()                # DictCursor, autocommit=True, utf8mb4
   ├─ query / query_one / execute / executemany
   ├─ txn()                    # context manager — rolls back on exit
   ├─ assert_row_count(table, where, params, expected)
   ├─ cleanup_test_rows(table, where, params)
   └─ close()
```

The surface is intentionally identical to `PostgresClient` — this lets tests target either engine with minimal change.

---

## 3. Connection

```yaml
databases:
  mysql:
    host: dev-mysql.example.com
    port: 3306
    db:   appdb
    user_env: MYSQL_USER
    password_env: MYSQL_PASSWORD
```

`charset="utf8mb4"` is set in the connection — required for full Unicode (emoji, supplementary plane). The default `utf8` in MySQL is a 3-byte alias and silently truncates 4-byte chars.

---

## 4. Reading & writing

Same API as Postgres:

```python
rows = context.mysql.query("SELECT * FROM audit_log WHERE action = %s", ["users.list"])
context.mysql.execute("INSERT INTO audit_log (action, actor) VALUES (%s, %s)", ["x", "qa"])
```

Placeholder is `%s` for both engines — `pymysql` and `psycopg` happen to share the syntax.

---

## 5. MySQL-specific quirks worth knowing

- **`LAST_INSERT_ID()`.** Use it after `INSERT` if your table has `AUTO_INCREMENT`:
  ```python
  context.mysql.execute("INSERT INTO orders (...) VALUES (...)", [...])
  new_id = context.mysql.query_one("SELECT LAST_INSERT_ID() AS id")["id"]
  ```
- **`ON DUPLICATE KEY UPDATE`** for idempotent seeding:
  ```sql
  INSERT INTO users (...) VALUES (...) ON DUPLICATE KEY UPDATE updated_at = NOW();
  ```
- **Transaction isolation default is `REPEATABLE READ`.** This can mask uncommitted side effects from another session — be explicit when testing cross-session visibility.

---

## 6. Sample step usage

The `db_steps.py` file already exposes:

```gherkin
Then MySQL table "audit_log" should have 1 rows where action = 'users.list'
```

For more complex queries, write a custom step:

```python
@then('the latest audit row for "{action}" should be from actor "{actor}"')
def step(context, action, actor):
    row = context.mysql.query_one(
        "SELECT actor FROM audit_log WHERE action = %s ORDER BY id DESC LIMIT 1",
        [action],
    )
    assert row and row["actor"] == actor
```

---

## 7. Best practices

- **Use `utf8mb4` everywhere.** Tests with emoji or non-BMP characters will fail mysteriously otherwise.
- **Don't test against the same database other CI jobs share.** Use a dedicated schema, or container-up a fresh MySQL via `docker-compose.yml`.
- **Cleanup with `WHERE`** — never `DELETE FROM table` without a predicate, even in tests.
- **Index your assertion columns.** Same advice as Postgres — your tests benefit too.
