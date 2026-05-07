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
def _split_where(where: str):
    """
    Tiny helper: parse `col = 'val'` style into ('col = %s', ['val']) so we can
    use the test framework's parameterised execution. Limited on purpose — for
    complex predicates write a custom step.
    """
    parts = [p.strip() for p in where.split("=", 1)]
    col = parts[0]
    val = parts[1].strip().strip("'").strip('"')
    return f"{col} = %s", [val]
