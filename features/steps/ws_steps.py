"""features/steps/ws_steps.py — WebSocket step definitions."""
import json

from behave import given, then, when


@given('I authenticate the WebSocket client with role "{role}"')
def step_ws_auth(context, role):
    context.ws.with_oauth(scope="read write" if role != "viewer" else "read")


@when('I send a WebSocket message and expect {n:d} replies within {sec:d} seconds')
def step_ws_send_recv(context, n, sec):
    payload = json.loads(context.text)
    context.ws_messages = context.ws.send_and_receive(payload, expect_messages=n, timeout_seconds=sec)


@when('I subscribe and stream for {sec:d} seconds')
def step_ws_stream(context, sec):
    payload = json.loads(context.text)
    context.ws_messages = context.ws.stream(payload, duration_seconds=sec)


@then('the WebSocket reply count should be at least {n:d}')
def step_ws_reply_count(context, n):
    assert len(context.ws_messages) >= n, f"Got {len(context.ws_messages)}"


@then('the first WebSocket reply field "{field}" should equal "{value}"')
def step_ws_first(context, field, value):
    cur = context.ws_messages[0]
    for p in field.split("."):
        cur = cur[p]
    assert str(cur) == value, f"Expected {field}={value}, got {cur}"
