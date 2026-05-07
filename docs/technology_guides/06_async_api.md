# 06 — API Testing: Async / Event-Driven (Kafka)

> **Source files:** `src/qaforge/api/async_api/kafka_client.py`, `features/steps/` (extend as needed).

---

## 1. Why Kafka deserves its own subpackage

Async/event-driven contracts have very different testing semantics from synchronous APIs:

- **No request/response pairing.** A single producer event can fan out into N consumer side-effects.
- **Eventual consistency.** Assertions need timeouts and polling, never sleeps.
- **Topic isolation.** Tests must use ephemeral consumer groups so they don't disturb production consumers.

QAForge models producer and consumer as separate classes so step authors can compose them: produce → poll → assert.

---

## 2. Architecture

```
KafkaTestProducer(cfg)
   ├─ start()
   ├─ send(topic, value, key=None)
   └─ stop()

KafkaTestConsumer(cfg, topic, group="qa-test")
   ├─ start()                       # auto_offset_reset="latest"
   ├─ poll(expected=N, timeout_seconds=T) -> [value, ...]
   └─ stop()
```

Both wrap `aiokafka` in a synchronous façade backed by a per-client event loop, mirroring the WebSocket client.

---

## 3. End-to-end pattern

```python
# Step file
producer = KafkaTestProducer(context.cfg).start()
context.cleanup.add(producer.stop)

consumer = KafkaTestConsumer(context.cfg, "orders.processed", group=f"qa-{uuid.uuid4()}").start()
context.cleanup.add(consumer.stop)

producer.send("orders.created", {"id": "ord-1", "total": 99.99})

events = consumer.poll(expected=1, timeout_seconds=10)
assert events[0]["orderId"] == "ord-1"
assert events[0]["status"] == "processed"
```

The unique consumer group per scenario is critical — otherwise parallel runs steal each other's messages.

---

## 4. Sample feature outline

```gherkin
@api @kafka @regression
Feature: Order lifecycle events

  Background:
    Given I am running against the "dev" environment

  @no_prod
  Scenario: Order creation triggers an order.processed event
    Given a Kafka producer for topic "orders.created"
    And a Kafka consumer for topic "orders.processed"
    When I publish an order with id "ord-1" and total 99.99
    Then within 10 seconds the consumer should receive an event with orderId "ord-1"
```

> Step definitions for these are not in the bundled `*_steps.py` files — they're a few lines following the pattern in §3. Drop them into `features/steps/kafka_steps.py`.

---

## 5. Schema validation

Kafka events should carry contracts too. Use the same `validate_against_contract`:

```python
from qaforge.api.contract_validator import validate_against_contract
validate_against_contract(events[0], "order.processed.v1")
```

Schemas live in `test_data/static/contracts/`.

---

## 6. Configuration

```yaml
api:
  async_api:
    kafka_brokers: ["kafka-dev-1:9092", "kafka-dev-2:9092"]
```

Multiple brokers for HA. In Docker compose, set `kafka_brokers: ["kafka:9092"]` and add a Kafka service.

---

## 7. Best practices

- **Unique consumer groups per scenario.** Use `f"qa-{uuid.uuid4()}"` as the group ID. This guarantees isolation.
- **`auto_offset_reset="latest"`** is the default and almost always correct — you only want messages produced after the consumer started.
- **Always use timeouts.** A `poll()` without a timeout will block forever if no message arrives.
- **Clean up.** `context.cleanup.add(producer.stop)` and same for the consumer.
- **JSON only by default.** For Avro/Protobuf payloads, swap the `value_serializer`/`value_deserializer` lambdas in `kafka_client.py`.
