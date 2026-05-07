"""features/steps/graphql_steps.py — GraphQL step definitions."""
import json

from behave import given, then, when

from qaforge.api.graphql.operations import (
    CREATE_USER_MUTATION,
    DELETE_USER_MUTATION,
    GET_USER_QUERY,
    LIST_USERS_QUERY,
)


@given('I authenticate the GraphQL client with role "{role}"')
def step_gql_auth(context, role):
    context.graphql.with_oauth(scope="read write" if role != "viewer" else "read")


@when('I run the listUsers query with page {page:d} and limit {limit:d}')
def step_gql_list(context, page, limit):
    context.gql_result = context.graphql.query(
        LIST_USERS_QUERY, variables={"page": page, "limit": limit}
    )


@when('I create a user via GraphQL mutation with')
def step_gql_create(context):
    payload = json.loads(context.text)
    context.gql_result = context.graphql.mutation(
        CREATE_USER_MUTATION, variables={"input": payload}
    )
    context.created_user_id = context.gql_result["createUser"]["id"]
    context.cleanup.add(
        lambda: context.graphql.mutation(DELETE_USER_MUTATION, variables={"id": context.created_user_id})
    )


@when('I fetch the created user via GraphQL')
def step_gql_get(context):
    context.gql_result = context.graphql.query(GET_USER_QUERY, variables={"id": context.created_user_id})


@then('the GraphQL response field "{field}" should equal "{value}"')
def step_gql_field(context, field, value):
    cur = context.gql_result
    for part in field.split("."):
        cur = cur[part]
    assert str(cur) == value, f"Expected {field}={value}, got {cur}"


@then('the GraphQL listUsers total should be at least {n:d}')
def step_gql_total(context, n):
    total = context.gql_result["users"]["total"]
    assert total >= n, f"Expected total >= {n}, got {total}"


@then('the GraphQL schema should expose query, mutation, and subscription roots')
def step_gql_schema(context):
    schema = context.graphql.introspect()["__schema"]
    assert schema["queryType"], "Missing query type"
    assert schema["mutationType"], "Missing mutation type"
