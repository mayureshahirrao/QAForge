# 10 — Database Testing: DynamoDB

> **Source files:** `src/qaforge/database/dynamo/client.py`, `features/steps/db_steps.py`.

---

## 1. Driver

`boto3==1.35.36`. We use the **resource-level** API (`boto3.resource("dynamodb")`) because it returns Python-native types (`int`, `str`, `dict`) instead of the verbose AttributeValue format (`{"S": "..."}`).

---

## 2. Architecture

```
DynamoTestClient(cfg)         # constructor builds the resource (no separate connect)
   ├─ table(name)             # raw boto3 Table object
   ├─ put_item(table, item)
   ├─ get_item(table, key)            -> dict | None
   ├─ query(table, key_name, key_value) -> [dict, ...]
   ├─ scan_filter(table, attr, val)     -> [dict, ...]
   ├─ assert_item_exists(table, key)
   └─ cleanup(table, keys)              -> int
```

Local DynamoDB (`dynamodb-local`) is supported by setting `databases.dynamo.endpoint` to `http://localhost:8000`. AWS is the default when `endpoint` is null.

---

## 3. Configuration

```yaml
databases:
  dynamo:
    region: us-east-1
    endpoint: null               # or "http://dynamo:8000" in docker-compose
```

For local, also set dummy AWS creds (boto3 still expects them):

```bash
export AWS_ACCESS_KEY_ID=dummy
export AWS_SECRET_ACCESS_KEY=dummy
export AWS_DEFAULT_REGION=us-east-1
```

The `docker-compose.yml` does this automatically for the `qaforge` service.

---

## 4. Read patterns

### `GetItem` (primary key lookup — fastest)

```python
item = context.dynamo.get_item("sessions", {"user_id": "u-123"})
```

### `Query` (partition-key match, optional sort-key range)

```python
items = context.dynamo.query("sessions", "user_id", "u-123")
```

For composite keys with a sort-key condition, use the raw table:

```python
from boto3.dynamodb.conditions import Key
context.dynamo.table("sessions").query(
    KeyConditionExpression=Key("user_id").eq("u-123") & Key("created_at").gt("2025-01-01"),
)
```

### `Scan` with filter (slow — last resort)

```python
items = context.dynamo.scan_filter("sessions", "ip", "10.0.0.1")
```

Avoid scans in CI: if the table grows, every test gets slower.

---

## 5. Write & cleanup

```python
context.dynamo.put_item("sessions", {
    "user_id": "u-123",
    "created_at": "2025-04-01T00:00:00Z",
    "expires_at": "2025-04-02T00:00:00Z",
    "ip": "10.0.0.1",
})

# bulk delete via cleanup
context.cleanup.add(lambda: context.dynamo.cleanup("sessions", [{"user_id": "u-123"}]))
```

`cleanup()` uses `batch_writer()` under the hood — automatically batches into 25-item DeleteItem calls.

---

## 6. Decimal vs float

DynamoDB stores all numbers as `Decimal`. boto3 raises if you pass a `float`. Either convert up front:

```python
from decimal import Decimal
context.dynamo.put_item("orders", {"id": "o-1", "total": Decimal("99.99")})
```

…or cast received items in your assertions:

```python
assert float(item["total"]) == 99.99
```

---

## 7. Sample feature step

```gherkin
Then Dynamo table "sessions" should contain item with key "user_id"="u-123"
```

---

## 8. Best practices

- **Always provide the full key** to `get_item` (partition key + sort key, if the table has one). Missing the sort key returns `None` silently.
- **Use `query`, not `scan`.** Scans are O(table size).
- **Strongly consistent reads** are off by default — pass `ConsistentRead=True` to the raw table call when you've just written and need to read back immediately.
- **Provisioned vs on-demand** doesn't change test code, but on-demand tables won't throttle you in CI bursts.
- **For local sandbox,** the docker-compose stack includes `amazon/dynamodb-local`. Tables must be created beforehand — either by your app start-up or by a one-shot script.
