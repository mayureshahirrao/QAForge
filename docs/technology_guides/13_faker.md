# 13 — Faker (Dynamic Test Data)

> **Source files:** `src/qaforge/data/faker_factory.py`, `src/qaforge/data/loaders.py`.

---

## 1. Why Faker

Hardcoded test data has three problems:

1. **Collisions.** "alice@example.com" can't be created twice.
2. **Hidden assumptions.** Tests pass with a specific email format and silently break when a regex tightens.
3. **Repeatability theatre.** "Static" data still drifts — someone edits it and breaks unrelated suites.

Faker generates plausible, unique values for the dozens of fields a real domain has — names, addresses, phone numbers, dates, financial data, and so on.

---

## 2. Setup

```bash
pip install faker==30.3.0
```

QAForge instantiates a single module-level `faker = Faker()` in `data/faker_factory.py`. All factory functions reuse it.

---

## 3. The factory pattern

Don't sprinkle `faker.email()` calls across step files. Instead, define **payload factories** that return whole, valid domain objects:

```python
def user_payload(role: str = "viewer") -> Dict[str, Any]:
    return {
        "email": unique_email(),
        "fullName": faker.name(),
        "role": role,
        "phone": faker.phone_number(),
        "address": {
            "street": faker.street_address(),
            "city": faker.city(),
            "country": faker.country_code(),
            "postal": faker.postcode(),
        },
    }
```

This way:

- Tests are short: `context.user = user_payload(role="admin")`.
- Schema changes happen in one place.
- Composing payloads (`order_payload(user_id)`) becomes trivial.

---

## 4. Uniqueness

Faker's `email()` will eventually repeat. For unique values, mix in a UUID:

```python
def unique_email(domain: str = "qaforge.test") -> str:
    return f"qa.{uuid.uuid4().hex[:10]}@{domain}"
```

10 hex chars = 16^10 ≈ 1.1 trillion combinations — plenty.

---

## 5. Determinism for debugging

Sometimes you want a flake to be reproducible. Set the seed:

```bash
QAFORGE_FAKER_SEED=42 behave features/api/rest/users.feature
```

`faker_factory.py` reads this env var and calls `Faker.seed(...)` at import time. UUID-based fields (like `unique_email`) are still random — by design — but Faker-generated names, addresses, etc. become deterministic.

---

## 6. Locales

Default is `en_US`. To generate Indian names and addresses for a region-specific suite:

```python
from faker import Faker
in_faker = Faker("en_IN")
in_faker.name()       # Indian-sounding names
in_faker.address()    # Indian addresses
```

For a full multi-locale rollout, edit `faker_factory.py` to take a `locale` argument or build per-locale factories.

---

## 7. Rich examples

```python
from qaforge.data.faker_factory import faker

faker.iso8601()                              # 2025-04-09T14:32:11
faker.pyint(min_value=1, max_value=100)
faker.pydecimal(left_digits=3, right_digits=2, positive=True)
faker.boolean(chance_of_getting_true=70)
faker.uuid4()
faker.color_name(), faker.color()
faker.user_agent()
faker.ipv4(), faker.ipv6(), faker.mac_address()
faker.credit_card_number(card_type="visa")
faker.iban(), faker.bban(), faker.swift()
faker.text(max_nb_chars=200)
faker.sentence(nb_words=8)
faker.paragraph(nb_sentences=4)
faker.image_url()
```

Avoid using `credit_card_number()` against any real payment system — even sandbox. Faker's numbers pass Luhn but are not guaranteed test-card numbers.

---

## 8. Best practices

- **Compose, don't sprinkle.** `user_payload()` not 12 inline `faker.*()` calls.
- **Always wrap with `unique_*` helpers** for fields with uniqueness constraints (email, username).
- **Pair Faker with cleanup.** Every dynamic record you create should have a registered cleanup callable so failures don't leak data.
- **Don't overfit your assertions.** Asserting `result["fullName"] == "John Doe"` after `user_payload()` will fail every time — assert on shape (`isinstance(name, str)`), or store the generated value in `context.user` and refer back to it.
