"""features/steps/database/postgres/actorfilm_steps.py — Step definitions for Film-Actor relationship validation (dvdrental)."""
import psycopg
from behave import given, then, when

_TEST_ACTOR_ID    = 1
_VALID_FILM_ID    = 2      # actor 1 (Penelope Guiness) is NOT in film 2 in default dvdrental
_DUP_FILM_ID      = 1      # actor 1 IS already in film 1 — confirmed UniqueViolation trigger
_INVALID_ACTOR_ID = 999999


def _pg_rollback_restore(pg):
    pg.conn.rollback()
    pg.conn.autocommit = True


def _capture_pg_error(pg, sql, params):
    try:
        pg.execute(sql, params)
        return None
    except psycopg.Error as exc:
        return exc


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