"""
qaforge.data.faker_factory
==========================
Dynamic test data via Faker. Use deterministic seeding when a scenario
must be reproducible (set `QAFORGE_FAKER_SEED` env var).

Each factory returns a plain dict so it composes with REST/GraphQL/DB layers.
"""
from __future__ import annotations

import os
import uuid
from typing import Any, Dict, List

from faker import Faker

_seed = os.environ.get("QAFORGE_FAKER_SEED")
faker = Faker()
if _seed is not None:
    Faker.seed(int(_seed))


def unique_email(domain: str = "qaforge.test") -> str:
    return f"qa.{uuid.uuid4().hex[:10]}@{domain}"


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


def order_payload(user_id: str, items: int = 3) -> Dict[str, Any]:
    return {
        "userId": user_id,
        "items": [
            {
                "sku": faker.bothify("SKU-####-??").upper(),
                "qty": faker.random_int(min=1, max=5),
                "price": float(faker.pydecimal(left_digits=3, right_digits=2, positive=True)),
            }
            for _ in range(items)
        ],
        "currency": "USD",
        "createdAt": faker.iso8601(),
    }


def bulk_users(n: int, role: str = "viewer") -> List[Dict[str, Any]]:
    return [user_payload(role=role) for _ in range(n)]
