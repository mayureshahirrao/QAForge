# 03 — API Testing: GraphQL

> **Source files:** `src/qaforge/api/graphql/client.py`, `src/qaforge/api/graphql/operations.py`, `features/steps/graphql_steps.py`, `features/api/graphql/users.feature`.

---

## 1. Why a separate client (and not just `requests.post(json={"query": ...})`)

- **Schema-aware errors.** `gql` parses queries, so syntactic problems blow up before the request goes out.
- **Variables.** `variable_values=` is safer than f-string interpolation into a `query` field.
- **Subscriptions.** Easy to swap the HTTP transport for `WebsocketsTransport` when needed.

---

## 2. Architecture

```
GraphQLClient(cfg, auth)
   │
   ├─ with_oauth(scope)
   ├─ query(document, variables)
   ├─ mutation(document, variables)
   └─ introspect()

Operations (operations.py)
   ├─ GET_USER_QUERY
   ├─ LIST_USERS_QUERY
   ├─ CREATE_USER_MUTATION
   └─ DELETE_USER_MUTATION
```

Operations are kept in `operations.py` — never inline GraphQL strings in step files.

---

## 3. Building a query

```python
from qaforge.api.graphql.operations import LIST_USERS_QUERY
result = context.graphql.query(LIST_USERS_QUERY, variables={"page": 1, "limit": 20})
# result == {"users": {"items": [...], "total": 42, "page": 1, "limit": 20}}
```

The result is the `data` field — `gql` raises on `errors`.

---

## 4. Mutations

```python
result = context.graphql.mutation(
    """
    mutation CreateUser($input: CreateUserInput!) {
      createUser(input: $input) { id email }
    }
    """,
    variables={"input": {"email": "a@b.c", "fullName": "A", "role": "viewer"}},
)
created_id = result["createUser"]["id"]
```

For cleanup, register the inverse mutation:

```python
context.cleanup.add(lambda: context.graphql.mutation(DELETE_USER_MUTATION, variables={"id": created_id}))
```

---

## 5. Introspection

`context.graphql.introspect()` returns the `__schema` block — useful for smoke-testing that a GraphQL endpoint is reachable and exposes the expected root types. The included scenario `Schema introspection` does exactly that.

---

## 6. Subscriptions (planned)

The current client uses `RequestsHTTPTransport`. For subscriptions, swap to `WebsocketsTransport` from `gql.transport.websockets`:

```python
from gql.transport.websockets import WebsocketsTransport
transport = WebsocketsTransport(url=cfg.api.graphql.endpoint.replace("https", "wss"))
```

Wire it into `_ensure_client` behind a feature flag if you need real-time scenarios.

---

## 7. Sample feature

```gherkin
@api @graphql @regression
Feature: Users GraphQL API

  Background:
    Given I am running against the "dev" environment
    And I authenticate the GraphQL client with role "admin"

  Scenario: List users via query
    When I run the listUsers query with page 1 and limit 10
    Then the GraphQL listUsers total should be at least 1

  @no_prod
  Scenario: Create then fetch a user via mutation
    When I create a user via GraphQL mutation with
      """
      {"email": "gql.user@example.com", "fullName": "GQL User", "role": "viewer"}
      """
    And I fetch the created user via GraphQL
    Then the GraphQL response field "user.email" should equal "gql.user@example.com"
```

---

## 8. Best practices

- **One operation, one constant.** All GraphQL strings live in `operations.py` — searchable, versionable, mockable.
- **Always pass `variables=`.** Never inject values into the query string.
- **Treat `errors` as a hard failure.** `gql` raises by default; don't swallow.
- **Don't fragment-bomb.** GraphQL is happy to return huge nested results — keep test queries lean to limit blast radius.
