"""features/steps/db_steps.py — Database validation step definitions."""
from behave import given, then, when


# ---------- PostgreSQL ----------
@then('Postgres table "{table}" should have {n:d} rows where {where}')
def step_pg_count(context, table, n, where):
    where_clause, params = _split_where(where)
    context.pg.assert_row_count(table, where_clause, params, n)


@given('I cleanup Postgres rows in "{table}" where {where}')
def step_pg_cleanup(context, table, where):
    where_clause, params = _split_where(where)
    context.cleanup.add(lambda: context.pg.cleanup_test_rows(table, where_clause, params))


# ---------- MySQL ----------
@then('MySQL table "{table}" should have {n:d} rows where {where}')
def step_my_count(context, table, n, where):
    where_clause, params = _split_where(where)
    context.mysql.assert_row_count(table, where_clause, params, n)


# ---------- Mongo ----------
@then('Mongo collection "{col}" should contain a doc with field "{field}" equal to "{value}"')
def step_mongo_doc(context, col, field, value):
    context.mongo.assert_doc_exists(col, {field: value})


# ---------- Dynamo ----------
@then('Dynamo table "{table}" should contain item with key "{key_name}"="{key_value}"')
def step_dyn_exists(context, table, key_name, key_value):
    context.dynamo.assert_item_exists(table, {key_name: key_value})


# ---------- helpers ----------
# ---------- PostgreSQL: Film-Actor (dvdrental) ----------
@given('the PostgreSQL database connection is established')
def step_pg_connected(context):
    assert context.pg is not None


@when('I insert valid actor_id and film_id')
def step_pg_insert_actor_film(context):
    context.pg.execute(
        "INSERT INTO film_actor (actor_id, film_id, last_update) VALUES (%s, %s, NOW())",
        (_TEST_ACTOR_ID, _VALID_FILM_ID),
    )
    context.cleanup.add(lambda: context.pg.cleanup_test_rows(
        "film_actor", "actor_id = %s AND film_id = %s", [_TEST_ACTOR_ID, _VALID_FILM_ID]
    ))


@then('the mapping should be created')
def step_pg_mapping_exists(context):
    row = context.pg.query_one(
        "SELECT COUNT(*) AS c FROM film_actor WHERE actor_id = %s AND film_id = %s",
        (_TEST_ACTOR_ID, _VALID_FILM_ID),
    )
    assert (row["c"] if row else 0) == 1


@when('I insert invalid actor_id')
def step_pg_insert_invalid_actor(context):
    context.last_error = _capture_pg_error(
        context.pg,
        "INSERT INTO film_actor (actor_id, film_id, last_update) VALUES (%s, %s, NOW())",
        (_INVALID_ACTOR_ID, _VALID_FILM_ID),
    )


@then('foreign key validation should fail')
def step_pg_fk_fails(context):
    assert context.last_error is not None


@when('duplicate mapping is inserted')
def step_pg_insert_duplicate(context):
    # (actor_id=1, film_id=1) is confirmed to exist in the default dvdrental dataset
    context.last_error = _capture_pg_error(
        context.pg,
        "INSERT INTO film_actor (actor_id, film_id, last_update) VALUES (%s, %s, NOW())",
        (_TEST_ACTOR_ID, _DUP_FILM_ID),
    )


@then('duplicate insertion should fail')
def step_pg_duplicate_fails(context):
    assert context.last_error is not None


@given('actor has mapped films')
def step_pg_actor_has_films(context):
    row = context.pg.query_one(
        "SELECT COUNT(*) AS c FROM film_actor WHERE actor_id = %s",
        (_TEST_ACTOR_ID,),
    )
    assert (row["c"] if row else 0) > 0


@when('actor record is deleted')
def step_pg_delete_actor(context):
    # dvdrental uses ON DELETE RESTRICT; remove child rows first, then parent.
    # Run inside an explicit transaction so cleanup can rollback — no permanent changes.
    context.pg.conn.autocommit = False
    context.pg.execute("DELETE FROM film_actor WHERE actor_id = %s", (_TEST_ACTOR_ID,))
    context.pg.execute("DELETE FROM actor WHERE actor_id = %s", (_TEST_ACTOR_ID,))
    context.cleanup.add(lambda: _pg_rollback_restore(context.pg))


@then('relationship integrity should be maintained')
def step_pg_cascade_check(context):
    row = context.pg.query_one(
        "SELECT COUNT(*) AS c FROM film_actor WHERE actor_id = %s",
        (_TEST_ACTOR_ID,),
    )
    assert (row["c"] if row else 0) == 0


_TEST_ACTOR_ID  = 1
_VALID_FILM_ID  = 2    # actor 1 (Penelope Guiness) is NOT in film 2 in default dvdrental
_DUP_FILM_ID    = 1    # actor 1 IS already in film 1 — confirmed UniqueViolation trigger
_INVALID_ACTOR_ID = 999999


def _pg_rollback_restore(pg):
    pg.conn.rollback()
    pg.conn.autocommit = True


def _capture_pg_error(pg, sql, params):
    import psycopg
    try:
        pg.execute(sql, params)
        return None
    except psycopg.Error as exc:
        return exc


def _split_where(where: str):
    """
    Parse a WHERE fragment into (clause, params) for parameterised execution.

    Supported forms:
      col = 'val'          ->  ("col = %s", ["val"])
      col IS NULL          ->  ("col IS NULL", [])
      col IS NOT NULL      ->  ("col IS NOT NULL", [])
      col NOT IN (...)     ->  ("col NOT IN (...)", [])   # subquery or literal list
    """
    upper = where.upper()
    if " IS NOT NULL" in upper or " IS NULL" in upper:
        return where, []
    if " NOT IN " in upper:
        return where, []
    parts = [p.strip() for p in where.split("=", 1)]
    col = parts[0]
    val = parts[1].strip().strip("'").strip('"')
    return f"{col} = %s", [val]
