# 09 — Database Testing: MongoDB

> **Source files:** `src/qaforge/database/mongo/client.py`, `features/steps/db_steps.py`.

---

## 1. Driver

`pymongo==4.10.1` — the official synchronous driver. Works fine inside Behave's sync model.

---

## 2. Architecture

```
MongoTestClient(cfg)
   ├─ connect()                          # builds MongoClient(uri, tz_aware=True)
   ├─ collection(name)                   # raw pymongo.Collection access
   ├─ insert_one(col, doc)        -> str(_id)
   ├─ find(col, filt, limit)      -> [doc, ...]
   ├─ count(col, filt)            -> int
   ├─ assert_doc_exists(col, filt)
   ├─ cleanup(col, filt)          -> deleted_count
   └─ close()
```

The default `tz_aware=True` makes Mongo return timezone-aware `datetime` objects, which avoids the most common mistake when asserting on timestamps.

---

## 3. Connection

```yaml
databases:
  mongo:
    uri_env: MONGO_URI                  # e.g. "mongodb://user:pass@host:27017"
    db: appdb
```

Why an env var for the URI rather than separate host/user/pass? Because Mongo URIs typically embed replica-set parameters, TLS options, and read preferences that don't decompose cleanly. One env var keeps the contract simple.

---

## 4. Reading & writing

```python
# create
new_id = context.mongo.insert_one(
    "events",
    {"type": "user.login", "user_id": "u-123", "at": datetime.utcnow()},
)
context.cleanup.add(lambda: context.mongo.cleanup("events", {"_id": ObjectId(new_id)}))

# read
docs = context.mongo.find("events", {"user_id": "u-123"}, limit=10)
assert any(d["type"] == "user.login" for d in docs)

# count
n = context.mongo.count("events", {"type": "user.login"})
```

Need a richer query (aggregation pipeline)? Reach for the raw collection:

```python
pipeline = [
    {"$match": {"type": "user.login"}},
    {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
    {"$sort": {"count": -1}},
]
top = list(context.mongo.collection("events").aggregate(pipeline))
```

---

## 5. Indexes (test-side cheatsheet)

If you're asserting on a high-volume collection, ensure indexes exist:

```python
context.mongo.collection("events").create_index([("user_id", 1), ("at", -1)])
```

For test isolation, you can drop and recreate the test DB in a `before_all` hook (be careful — this is destructive).

---

## 6. ObjectId pitfalls

`_id` is a `bson.ObjectId`, not a string. When passing one back into a query, wrap it:

```python
from bson import ObjectId
doc = context.mongo.find("events", {"_id": ObjectId(some_string_id)})
```

The convenience `cleanup` accepts a filter dict, so you can just pass `{"_id": ObjectId(new_id)}`.

---

## 7. Sample feature step

```gherkin
Then Mongo collection "user_profiles" should contain a doc with field "email" equal to "alice@example.com"
```

---

## 8. Best practices

- **Use a dedicated test DB.** `appdb_qa` or similar — never share with prod.
- **Tag cleanup as `cleanup.add(...)`** — same as Postgres / MySQL.
- **Don't `find()` without a filter.** It's a full-collection scan.
- **`tz_aware=True` always.** Naive datetimes are landmines.
- **Watch for change-stream tests.** They require a replica set; standalone Mongo can't open change streams.
