"""Shared utilities for Petstore API step definitions (not a step file)."""
import json
from pathlib import Path

import jsonschema
import requests

BASE_URL = "https://petstore.swagger.io/v2"
CONTRACTS_DIR = Path(__file__).resolve().parents[4] / "test_data" / "static" / "contracts"

SECURITY_PATTERNS = (
    "traceback",
    "stack trace",
    "exception in",
    "syntax error",
    " sql ",
    "ora-",
    "pg::",
    "mysql_",
    "sqlite",
    "psycopg",
)


def load_contract(name: str) -> dict:
    path = CONTRACTS_DIR / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def validate_schema(data, schema: dict) -> None:
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    if errors:
        msgs = "\n".join(
            f"  - [{'.'.join(str(p) for p in e.absolute_path)}] {e.message}"
            for e in errors
        )
        raise AssertionError(f"Schema violations ({len(errors)}):\n{msgs}")


def assert_no_security_leak(response_text: str) -> None:
    lower = response_text.lower()
    hits = [p for p in SECURITY_PATTERNS if p in lower]
    assert not hits, f"Response leaks sensitive info — matched patterns: {hits}"


def make_pet_payload(fake) -> dict:
    return {
        "name": f"pet-{fake.uuid4()}",
        "photoUrls": ["https://example.com/photo.jpg"],
        "status": "available",
    }


def ensure_petstore_client(context) -> None:
    """Lazily initialize context.client for features that have no Background step."""
    if getattr(context, "client", None) is None:
        context.client = requests.Session()
        context.client.headers.update({
            "api_key": "special-key",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        context.cleanup.add(context.client.close)


def create_pet(client: requests.Session, fake) -> dict:
    r = client.post(f"{BASE_URL}/pet", json=make_pet_payload(fake))
    assert r.status_code == 200, f"Setup: create pet failed — {r.status_code} {r.text[:200]}"
    return r.json()


def create_order(client: requests.Session) -> dict:
    r = client.post(f"{BASE_URL}/store/order", json={
        "petId": 1, "quantity": 1, "status": "placed", "complete": False,
    })
    assert r.status_code == 200, f"Setup: create order failed — {r.status_code} {r.text[:200]}"
    return r.json()


def create_user(client: requests.Session, fake) -> dict:
    payload = {
        "username": f"u{fake.uuid4().replace('-', '')[:16]}",
        "firstName": fake.first_name(),
        "lastName": fake.last_name(),
        "email": fake.email(),
        "password": "Test1234!",
        "phone": fake.numerify("##########"),
        "userStatus": 0,
    }
    r = client.post(f"{BASE_URL}/user", json=payload)
    assert r.status_code == 200, f"Setup: create user failed — {r.status_code} {r.text[:200]}"
    return payload