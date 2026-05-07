# 07 — Database Testing: PostgreSQL

> **Source files:** `src/qaforge/database/postgres/client.py`, `features/steps/db_steps.py`, `features/database/persistence.feature`.

---

## 1. Driver choice

QAForge uses **psycopg 3** (`psycopg[binary]==3.2.3`). It's actively maintained (psycopg2 is in maintenance mode), has a clean async story (we don't use async here, but it future-proofs), and ships pre-built wheels.

---

## 2. Architecture

```
PostgresClient(cfg)
   ├─ connect()                         # autocommit=True, dict_row factory
   ├─ query(sql, params)        -> list[dict]
   ├─ query_one(sql, params)    -> dict | None
   ├─ execute(sql, params)      -> int (rowcount)
   ├─ executemany(sql, seq)
   ├─ txn()                              # context manager — rolls back on exit
   ├─ assert_row_count(table, where, params, expected)
   ├─ cleanup_test_rows(table, where, params)
   └─ close()
```

The connection is **autocommit by default** because tests usually want each statement to land independently. Switch to `txn()` when you need a rollback boundary (e.g. read-only sanity checks that must not leave traces).

---

## 3. Connection setup

In `config/environments/<env>.yaml`:

```yaml
databases:
  postgres:
    host: dev-pg.example.com
    port: 5432
    db:   appdb
    user_env: PG_USER
    password_env: PG_PASSWORD
```

Secrets are env-resolved (`PG_USER`, `PG_PASSWORD`). The client refuses to start if either is missing — fail fast over silent breakage.

---

## 4. Reading data

```python
# all rows
rows = context.pg.query(
    "SELECT id, email, role FROM users WHERE created_at > %s",
    [yesterday],
)
# first row only
row = context.pg.query_one(
    "SELECT * FROM users WHERE id = %s", [user_id]
)
```

Rows are dicts (psycopg's `dict_row` factory). Access via `row["email"]`.

---

## 5. Writing data

```python
n = context.pg.execute(
    "INSERT INTO audit_log (action, actor) VALUES (%s, %s)",
    ["users.list", "qa-bot"],
)
assert n == 1
```

For batches:

```python
context.pg.executemany(
    "INSERT INTO audit_log (action, actor) VALUES (%s, %s)",
    [("a", "x"), ("b", "y"), ("c", "z")],
)
```

---

## 6. Transactions for read-only safety

Sometimes a test asserts on the state of the DB after a side effect, but you want to be paranoid about committing nothing yourself:

```python
with context.pg.txn():
    context.pg.execute("INSERT INTO probes(...) VALUES(...)")
    rows = context.pg.query("SELECT ... FROM probes WHERE ...")
    assert rows
# upon exit, everything rolls back
```

---

## 7. Consistency checks (read after write across services)

REST creates a user → Postgres should reflect it. The pattern:

```gherkin
Given I authenticate the REST client with role "admin"
And a freshly generated user with role "viewer"
And I cleanup Postgres rows in "users" where email = '{user.email}'
When I create a user from the generated payload
Then the response status should be 201
And Postgres table "users" should have 1 rows where email = '{user.email}'
```

The `cleanup` step registers a `DELETE` to run in `after_scenario` — even if the test fails midway, no rows leak.

---

## 8. SQL injection — what QAForge prevents and what it doesn't

- **Always parametrise values.** `%s` placeholders bind safely (`psycopg` handles escaping).
- **Identifiers (`table`, column names, `WHERE` clauses) are not user input** in this framework — tests author them. The `_split_where` helper in `db_steps.py` is intentionally minimal; for complex predicates, write a custom step rather than extending the helper.

---

## 9. Best practices

- **Index on the columns you assert against.** Test queries on big tables benefit from proper indexes too.
- **Use `LIMIT` in tests.** Even if you only fetch one row, `LIMIT 1` prevents accidental full-table reads.
- **Read replicas in prod.** `prod.yaml` points at `prod-pg-readonly.example.com` — your tests can run safely against prod for smoke without ever risking a write.
- **Clean up reliably.** Use `context.cleanup.add(...)` instead of trying to delete at the end of a step (a failure earlier in the step would skip the delete).
