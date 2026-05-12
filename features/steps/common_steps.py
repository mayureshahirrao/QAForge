"""
features/steps/common_steps.py
==============================
Cross-cutting steps (auth setup, environment switching, generic waits).
"""
import requests
from behave import given, then, when

from qaforge.data.faker_factory import faker, user_payload
from qaforge.data.loaders import static_user

_PETSTORE_BASE = "https://petstore.swagger.io/v2"


@given('I am running against the "{env}" environment')
def step_assert_env(context, env):
    assert context.cfg.environment == env, (
        f"Expected env={env}, but config loaded {context.cfg.environment}. "
        f"Run with: behave -D env={env}"
    )


@given('a known user "{key}"')
def step_known_user(context, key):
    context.user = static_user(key)


@given('a freshly generated user with role "{role}"')
def step_random_user(context, role):
    context.user = user_payload(role=role)


@given('I have an OAuth token for role "{role}"')
def step_oauth_role(context, role):
    context.token = context.auth.assume_role(role)


@then('the response status should be {status:d}')
@then('response status should be {status:d}')
def step_status(context, status):
    actual = getattr(context, "response_status", None)
    assert actual == status, f"Expected {status}, got {actual}"


# ---------------------------------------------------------------------------
# Petstore API shared setup
# ---------------------------------------------------------------------------

@given('Swagger Petstore API is available')
def step_petstore_api_available(context):
    context.client = requests.Session()
    context.client.headers.update({
        "api_key": "special-key",
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
    context.cleanup.add(context.client.close)


@given('valid request headers are configured')
def step_valid_request_headers(context):
    # Headers are already set in 'Swagger Petstore API is available'.
    # This step exists as an explicit checkpoint in the Background.
    assert "api_key" in context.client.headers, "api_key header not configured"
    assert context.client.headers.get("Content-Type") == "application/json"
