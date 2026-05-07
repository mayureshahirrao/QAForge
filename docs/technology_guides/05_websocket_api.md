# 05 — API Testing: WebSockets

> **Source files:** `src/qaforge/api/websocket/client.py`, `features/steps/ws_steps.py`, `features/api/websocket/notifications.feature`.

---

## 1. The sync/async tension (and how QAForge resolves it)

Behave step files are synchronous. The `websockets` library is async-first. QAForge wraps the async API in a synchronous façade backed by a per-client `asyncio` event loop. The result: step authors stay in a sync mental model.

```python
WebSocketClient(cfg, auth)
   ├─ with_oauth(scope)
   ├─ send_and_receive(msg, expect_messages=N, timeout_seconds=T) -> [reply, ...]
   ├─ stream(send_message, duration_seconds=T)                    -> [event, ...]
   └─ close()
```

---

## 2. Two interaction patterns

### 2.1  Send, receive N replies, close

For request/response over WebSocket (e.g. ping/pong, command/ack):

```python
replies = context.ws.send_and_receive(
    {"type": "ping", "id": "abc"},
    expect_messages=1,
    timeout_seconds=5,
)
assert replies[0]["type"] == "pong"
```

If fewer than N messages arrive before timeout, the partial list is returned and a warning is logged — the test then asserts on what it got.

### 2.2  Subscribe, drain for a fixed duration

For event streams (live notifications, telemetry):

```python
events = context.ws.stream({"type": "subscribe", "channel": "system.health"}, duration_seconds=3)
assert len(events) >= 1
```

This pattern is intentionally bounded by wall clock so tests can't hang forever.

---

## 3. Authentication

Bearer tokens flow through `additional_headers` on connect:

```python
context.ws.with_oauth(scope="read")          # caches token
context.ws.send_and_receive(...)             # token is set as Authorization header
```

If your server uses a query-string token (`?token=...`), edit `WebSocketClient.url` before connecting.

---

## 4. Reconnection scenarios

The current client opens a fresh connection per call. For reconnect tests, write a step that:

1. Sends an initial message.
2. Forces a disconnect (server-side trigger via REST, or close the loop).
3. Sends another message and verifies the server resumed state.

Pattern:

```python
@when('I send a flap-the-connection scenario')
def step(context):
    context.ws.send_and_receive({"type": "subscribe"}, 1, 5)
    # simulate disconnect via control plane
    context.rest.post("/admin/disconnect-test-clients")
    context.ws.send_and_receive({"type": "ping"}, 1, 5)
```

---

## 5. Sample feature

```gherkin
@api @websocket @regression
Feature: Real-time WebSocket notifications

  Background:
    Given I am running against the "dev" environment
    And I authenticate the WebSocket client with role "admin"

  Scenario: Subscribe to notifications and assert echo
    When I send a WebSocket message and expect 1 replies within 5 seconds
      """
      {"type": "ping", "id": "abc"}
      """
    Then the WebSocket reply count should be at least 1
    And the first WebSocket reply field "type" should equal "pong"

  Scenario: Stream live notifications for 3 seconds
    When I subscribe and stream for 3 seconds
      """
      {"type": "subscribe", "channel": "system.health"}
      """
    Then the WebSocket reply count should be at least 1
```

---

## 6. Best practices

- **Always set a `duration` or `timeout`.** WebSocket tests without timeouts hang CI.
- **Don't assert exact message counts in stream tests.** The server's emission rate varies. Use `>=`.
- **Always close the client.** `environment.py` registers `context.ws.close` in cleanup automatically.
