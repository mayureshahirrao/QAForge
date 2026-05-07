"""
qaforge.api.contract_validator
==============================
JSON-schema based response contract validation. Schemas live in
`test_data/static/contracts/*.json`.

Usage:
    validate_against_contract(response.json(), "user.v1")
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError

CONTRACTS_DIR = Path(__file__).resolve().parents[3] / "test_data" / "static" / "contracts"


@lru_cache(maxsize=64)
def _load_schema(name: str) -> dict:
    fp = CONTRACTS_DIR / f"{name}.json"
    if not fp.exists():
        raise FileNotFoundError(f"Contract schema not found: {fp}")
    return json.loads(fp.read_text())


def validate_against_contract(payload, contract_name: str) -> None:
    """Validate `payload` against `<contract_name>.json`. Raises ValidationError on mismatch."""
    schema = _load_schema(contract_name)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda e: e.path)
    if errors:
        msgs = "\n  - ".join(f"{list(e.path)}: {e.message}" for e in errors)
        raise ValidationError(f"Contract {contract_name} violated:\n  - {msgs}")
