"""features/steps/api/rest/user_steps.py — Petstore User Management step definitions.

Covers:
  features/api/rest/user_management.feature
"""
from behave import given, then, when
from faker import Faker

from api.rest._petstore_helpers import (
    BASE_URL,
    SECURITY_PATTERNS,
    assert_no_security_leak,
    create_user,
)

fake = Faker()

_SQL_INJECTION = "' OR '1'='1'; DROP TABLE users; --"


def _fresh_username() -> str:
    return f"u{fake.uuid4().replace('-', '')[:20]}"


# ---------------------------------------------------------------------------
# GIVEN
# ---------------------------------------------------------------------------

@given('valid user payload')
def step_valid_user_payload(context):
    context.username = _fresh_username()
    context.payload = {
        "username": context.username,
        "firstName": fake.first_name(),
        "lastName": fake.last_name(),
        "email": fake.email(),
        "password": "Test1234!",
        "phone": fake.numerify("##########"),
        "userStatus": 0,
    }


@given('valid users list payload')
def step_valid_users_list_payload(context):
    users = [
        {
            "username": _fresh_username(),
            "firstName": fake.first_name(),
            "lastName": fake.last_name(),
            "email": fake.email(),
            "password": "Test1234!",
            "phone": fake.numerify("##########"),
            "userStatus": 0,
        }
        for _ in range(3)
    ]
    context.payload = users
    context.created_usernames = [u["username"] for u in users]


@given('valid username and password')
def step_valid_username_and_password(context):
    user = create_user(context.client, fake)
    context.username = user["username"]
    context.login_params = {"username": user["username"], "password": "Test1234!"}
    uname = user["username"]
    context.cleanup.add(lambda: context.client.delete(f"{BASE_URL}/user/{uname}"))


@given('invalid username and password')
def step_invalid_username_and_password(context):
    context.login_params = {"username": "no_such_user_xyz_99", "password": "wrongpassword"}


@given('SQL injection username')
def step_sql_injection_username(context):
    context.login_params = {"username": _SQL_INJECTION, "password": "anything"}


@given('existing username')
def step_existing_username(context):
    user = create_user(context.client, fake)
    context.username = user["username"]
    uname = user["username"]
    context.cleanup.add(lambda: context.client.delete(f"{BASE_URL}/user/{uname}"))


@given('invalid username')
def step_invalid_username(context):
    context.username = f"no-such-user-{fake.uuid4()}"


@given('existing user payload')
def step_existing_user_payload(context):
    user = create_user(context.client, fake)
    context.username = user["username"]
    context.payload = {
        "username": context.username,
        "firstName": fake.first_name(),
        "lastName": fake.last_name(),
        "email": fake.email(),
        "password": "Updated1234!",
        "phone": fake.numerify("##########"),
        "userStatus": 1,
    }
    uname = context.username
    context.cleanup.add(lambda: context.client.delete(f"{BASE_URL}/user/{uname}"))


@given('invalid user payload')
def step_invalid_user_payload(context):
    context.username = _fresh_username()
    # empty username violates the API contract
    context.payload = {"username": ""}


@given('deleted username credentials')
def step_deleted_username_credentials(context):
    user = create_user(context.client, fake)
    uname = user["username"]
    context.client.delete(f"{BASE_URL}/user/{uname}")
    context.login_params = {"username": uname, "password": "Test1234!"}


# ---------------------------------------------------------------------------
# WHEN
# ---------------------------------------------------------------------------

@when('user sends POST request to "/user"')
def step_post_user(context):
    r = context.client.post(f"{BASE_URL}/user", json=context.payload)
    context.response = r
    context.response_status = r.status_code
    if r.status_code == 200 and getattr(context, "username", None):
        uname = context.username
        context.cleanup.add(lambda: context.client.delete(f"{BASE_URL}/user/{uname}"))


@when('user sends POST request to "/user/createWithList"')
def step_post_user_create_list(context):
    r = context.client.post(f"{BASE_URL}/user/createWithList", json=context.payload)
    context.response = r
    context.response_status = r.status_code
    if r.status_code == 200:
        for uname in getattr(context, "created_usernames", []):
            _u = uname
            context.cleanup.add(lambda u=_u: context.client.delete(f"{BASE_URL}/user/{u}"))


@when('user sends GET request to "/user/login"')
def step_get_user_login(context):
    r = context.client.get(f"{BASE_URL}/user/login", params=context.login_params)
    context.response = r
    context.response_status = r.status_code


@when('user sends GET request to "/user/{{username}}"')
def step_get_user(context):
    r = context.client.get(f"{BASE_URL}/user/{context.username}")
    context.response = r
    context.response_status = r.status_code


@when('user sends PUT request to "/user/{{username}}"')
def step_put_user(context):
    r = context.client.put(f"{BASE_URL}/user/{context.username}", json=context.payload)
    context.response = r
    context.response_status = r.status_code


@when('user sends DELETE request to "/user/{{username}}"')
def step_delete_user(context):
    r = context.client.delete(f"{BASE_URL}/user/{context.username}")
    context.response = r
    context.response_status = r.status_code


@when('user sends login request')
def step_user_sends_login_request(context):
    r = context.client.get(f"{BASE_URL}/user/login", params=context.login_params)
    context.response = r
    context.response_status = r.status_code


# ---------------------------------------------------------------------------
# THEN
# ---------------------------------------------------------------------------

@then('authentication token should be returned')
def step_auth_token_returned(context):
    # Petstore returns a session token string in the response body
    body = context.response.text
    assert (
        "logged in" in body.lower()
        or context.response.headers.get("X-Rate-Limit")
        or context.response.headers.get("X-Expires-After")
    ), f"No auth indicator in response: {body[:300]}"


@then('authentication should fail')
def step_authentication_should_fail(context):
    assert context.response_status in (400, 401, 403), (
        f"Expected 400/401/403 for failed auth, got {context.response_status}"
    )
    assert_no_security_leak(context.response.text)