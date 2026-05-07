"""features/steps/rest_steps.py — REST API step definitions."""
import json

from behave import given, then, when

from qaforge.api.contract_validator import validate_against_contract
from qaforge.api.rest.endpoints.users import UsersAPI


@given('I authenticate the REST client with role "{role}"')
def step_rest_auth(context, role):
    context.rest.with_role(role)
    context.users_api = UsersAPI(context.rest)


@given('I authenticate via password+OTP for "{email}"')
def step_rest_pwotp(context, email):
    from qaforge.data.loaders import static_user
    u = static_user(email)
    context.rest.with_password_otp(email=u["email"], password=u["password"], otp=u["otp"])
    context.users_api = UsersAPI(context.rest)


@when('I list users on page {page:d} with limit {limit:d}')
def step_list_users(context, page, limit):
    context.response = context.users_api.list_users(page=page, limit=limit)
    context.response_status = context.response.status_code


@when('I create a user from the generated payload')
def step_create_user(context):
    context.response = context.users_api.create_user(context.user)
    context.response_status = context.response.status_code
    if context.response.is_success:
        body = context.response.json()
        context.created_user_id = body["id"]
        context.cleanup.add(lambda: context.users_api.delete_user(context.created_user_id))


@when('I get the created user')
def step_get_user(context):
    context.response = context.users_api.get_user(context.created_user_id)
    context.response_status = context.response.status_code


@when('I patch the created user with')
def step_patch_user(context):
    payload = json.loads(context.text)
    context.response = context.users_api.update_user(context.created_user_id, payload)
    context.response_status = context.response.status_code


@then('the response body matches the "{contract}" contract')
def step_contract(context, contract):
    validate_against_contract(context.response.json(), contract)


@then('the response field "{field}" should equal "{value}"')
def step_field_equal(context, field, value):
    body = context.response.json()
    parts = field.split(".")
    cur = body
    for p in parts:
        cur = cur[p]
    assert str(cur) == value, f"Expected {field}={value}, got {cur}"


@then('the response should contain at least {n:d} items')
def step_min_items(context, n):
    body = context.response.json()
    items = body if isinstance(body, list) else body.get("items", [])
    assert len(items) >= n, f"Expected >= {n} items, got {len(items)}"
