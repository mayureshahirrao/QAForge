# 04 — API Testing: gRPC

> **Source files:** `src/qaforge/api/grpc/client.py`, `proto/user_service.proto`, `scripts/gen_grpc.sh`, `features/steps/grpc_steps.py`, `features/api/grpc/users.feature`.

---

## 1. Generating Python stubs

`.proto` files live in `proto/`. To (re)generate stubs:

```bash
bash scripts/gen_grpc.sh
```

The script runs `python -m grpc_tools.protoc` and patches the imports inside `*_pb2_grpc.py` so they work as a relative import inside `qaforge.api.grpc.generated`.

The generated artefacts (`user_service_pb2.py`, `user_service_pb2_grpc.py`) are gitignored — every dev / CI regenerates locally.

---

## 2. Architecture

```
GrpcClient(cfg, auth)
   ├─ connect()                 ── builds secure/insecure channel
   ├─ with_oauth(scope)         ── token cached for `auth_metadata()`
   ├─ stub(stub_class)          ── returns the generated stub bound to channel
   ├─ auth_metadata()           ── [("authorization", "Bearer ...")]
   └─ collect_server_stream(call) ── drains a server-streaming response
```

QAForge keeps generated stubs in their own subpackage so the runtime client stays decoupled.

---

## 3. RPC styles supported

The sample `user_service.proto` covers all four styles:

| Style              | RPC                                        | How to call                                                    |
| ------------------ | ------------------------------------------ | -------------------------------------------------------------- |
| Unary              | `GetUser(GetUserRequest) -> User`          | `stub.GetUser(req, metadata=...)`                              |
| Server streaming   | `ListUsers(ListUsersRequest) -> stream`    | `for u in stub.ListUsers(req, metadata=...): ...`              |
| Client streaming   | `CreateUsers(stream User) -> CreateUsersResponse` | `stub.CreateUsers(iter(users), metadata=...)`           |
| Bidi streaming     | `Chat(stream ChatMessage) -> stream`       | `for reply in stub.Chat(iter(msgs), metadata=...): ...`        |

---

## 4. Sample step (unary + server streaming)

```python
from qaforge.api.grpc.generated import user_service_pb2 as pb
from qaforge.api.grpc.generated import user_service_pb2_grpc as pb_grpc

# Authenticate once
context.grpc.with_oauth(scope="read")
stub = context.grpc.stub(pb_grpc.UserServiceStub)

# Unary
resp = stub.GetUser(pb.GetUserRequest(id="u-123"), metadata=context.grpc.auth_metadata())
assert resp.email == "alice@example.com"

# Server streaming
call = stub.ListUsers(pb.ListUsersRequest(page=1, limit=10), metadata=context.grpc.auth_metadata())
users = context.grpc.collect_server_stream(call)
assert len(users) >= 1
```

---

## 5. TLS, deadlines, retries

```python
# TLS toggle is in config
api:
  grpc:
    host: dev.grpc.example.com
    port: 443
    use_tls: true

# Per-RPC deadline (recommended in CI)
resp = stub.GetUser(req, metadata=meta, timeout=5)

# Retries via service config — set on channel creation if you need them
options = [("grpc.service_config", json.dumps({...}))]
grpc.secure_channel(target, creds, options=options)
```

QAForge uses `grpc.ssl_channel_credentials()` (system trust store). For mutual TLS, replace with `grpc.ssl_channel_credentials(root_certificates=, private_key=, certificate_chain=)`.

---

## 6. Sample feature

```gherkin
@api @grpc @regression
Feature: Users gRPC service

  Background:
    Given I am running against the "dev" environment
    And I authenticate the gRPC client with role "admin"

  Scenario: Unary GetUser
    When I call GetUser with id "u-123"
    Then the gRPC user response email should equal "alice@example.com"

  Scenario: Server streaming ListUsers
    When I call ListUsers (server streaming) with page 1 and limit 10
    Then the gRPC server stream should contain at least 1 users
```

---

## 7. Best practices

- **Always set a timeout** on RPC calls. Default behaviour is "wait forever".
- **Catch `grpc.RpcError`.** It exposes `.code()` (a `grpc.StatusCode`) and `.details()`.
- **Regenerate stubs in CI** — never check generated files into Git. The `gen_grpc.sh` script is fast and deterministic.
- **Channel reuse.** One channel per scenario is fine; opening a channel per RPC is wasteful (TLS handshake + DNS).
