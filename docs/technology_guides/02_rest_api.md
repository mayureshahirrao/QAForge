# 02 — API Testing: REST

> **Source files:** `src/qaforge/api/rest/client.py`, `src/qaforge/api/rest/endpoints/*.py`, `src/qaforge/api/auth_manager.py`, `src/qaforge/api/contract_validator.py`, `features/steps/rest_steps.py`, `features/api/rest/users.feature`.

---

## 1. Why a custom client over raw `requests`/`httpx`

- **Auth lifecycle** — tokens are cached, refreshed, and scoped centrally.
- **Domain wrappers** — endpoint groups (`UsersAPI`, `BillingAPI`, …) keep step files terse.
- **Logging** — every call emits `<METHOD> <path> -> <status> in <ms>`.
- **Replaceable** — swap `httpx` for `requests` by editing one class.

The client lives in `src/qaforge/api/rest/client.py`. Everything else builds on it.

---

## 2. Architecture

```
RestClient ─────► httpx.Client (base_url, timeout, default headers)
   │
   ├─ with_oauth(scope)            ◄── AuthManager.oauth_token
   ├─ with_password_otp(...)       ◄── AuthManager.password_otp_token
   └─ with_role(role)              ◄── AuthManager.assume_role

UsersAPI(rest)
   ├─ list_users(page, limit)
   ├─ get_user(id)
   ├─ create_user(payload)
   ├─ update_user(id, payload)
   └─ delete_user(id)
```

A scenario-level instance is built in `before_scenario` whenever the scenario carries `@api` or `@rest`.

---

## 3. Authentication

### OAuth client_credentials (service-to-service)

```python
context.rest.with_oauth(scope="read write")
```

Internally:

1. `AuthManager.oauth_token("read write")` — POSTs to `auth.oauth.token_url` with `grant_type=client_credentials`, `client_id`, `client_secret`.
2. The token is cached by scope until 30s before `expires_in`.

### Password + OTP (interactive user)

```python
context.rest.with_password_otp(email="alice@example.com", password="...", otp="123456")
```

Two-step:

1. POST `/auth/login` with email/password → `challenge_id`.
2. POST `/auth/otp` with `challenge_id` and `code` → access token.

### Role-based (RBAC scenarios)

```python
context.rest.with_role("viewer")   # under the hood: oauth_token(scope="read")
```

`assume_role` maps role names to scopes — extend the dictionary in `auth_manager.py` if you have more roles.

---

## 4. HTTP methods

```python
r = context.rest.get("/users", params={"page": 1, "limit": 20})
r = context.rest.post("/users", json={"email": "a@b.c", "fullName": "A"})
r = context.rest.put("/users/u-1", json={...})
r = context.rest.patch("/users/u-1", json={"fullName": "New"})
r = context.rest.delete("/users/u-1")
r = context.rest.head("/users/u-1")
```

`r` is `httpx.Response` — `.status_code`, `.json()`, `.text`, `.headers`, `.elapsed`.

> **4xx/5xx are not auto-raised.** Negative scenarios assert the failure status explicitly. If you want `raise_for_status()`, call it in your step.

---

## 5. Contract validation

Schemas live in `test_data/static/contracts/<id>.json` (Draft 2020-12). Reference others by `$id` for composition.

```python
from qaforge.api.contract_validator import validate_against_contract
validate_against_contract(response.json(), "user.v1")
```

Or in Gherkin:

```gherkin
Then the response body matches the "users.list.v1" contract
```

Failure messages list every JSON-pointer mismatch.

---

## 6. Endpoint wrapper recipe

To add a new endpoint group (`/billing/invoices`):

```python
# src/qaforge/api/rest/endpoints/billing.py
from qaforge.api.rest.client import RestClient

class BillingAPI:
    BASE = "/billing"
    def __init__(self, client: RestClient):
        self.client = client
    def list_invoices(self, **q):
        return self.client.get(f"{self.BASE}/invoices", params=q)
    def get_invoice(self, invoice_id: str):
        return self.client.get(f"{self.BASE}/invoices/{invoice_id}")
    def void_invoice(self, invoice_id: str):
        return self.client.post(f"{self.BASE}/invoices/{invoice_id}/void")
```

Then in `features/steps/rest_steps.py`:

```python
@when('I fetch invoice "{invoice_id}"')
def step(context, invoice_id):
    api = BillingAPI(context.rest)
    context.response = api.get_invoice(invoice_id)
    context.response_status = context.response.status_code
```

---

## 7. Sample feature (excerpt)

```gherkin
@api @rest @regression
Feature: Users REST API

  Background:
    Given I am running against the "dev" environment
    And I authenticate the REST client with role "admin"

  @no_prod
  Scenario: Create, fetch, patch a user
    Given a freshly generated user with role "viewer"
    When I create a user from the generated payload
    Then the response status should be 201
    And the response body matches the "user.v1" contract

  @rbac
  Scenario Outline: RBAC
    Given I authenticate the REST client with role "<role>"
    And a freshly generated user with role "viewer"
    When I create a user from the generated payload
    Then the response status should be <status>
    Examples:
      | role   | status |
      | viewer | 403    |
      | editor | 201    |
```

---

## 8. Best practices in QAForge

- **Always parametrise paths.** Build URLs with f-strings, never concat user data.
- **Register cleanup on creation.** When `create_user` returns 201, push `delete_user` to `context.cleanup`. The step file already does this — copy that pattern for new resources.
- **Never sleep waiting for a 200.** Use a poll loop with `tenacity` (`qaforge.core.retry.retry_on`) only when the API is genuinely eventually consistent.
- **Don't share tokens across roles.** `AuthManager` caches by scope; every role gets its own cache slot.
