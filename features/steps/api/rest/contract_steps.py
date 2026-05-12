"""features/steps/api/rest/contract_steps.py — OpenAPI Contract Validation step definitions.

Covers:
  features/api/rest/contract_validation.feature

NOTE: 'Given existing pet ID' is defined in pet_steps.py and shared via behave's global registry.
"""
from behave import given, then, when

from faker import Faker

from api.rest._petstore_helpers import (
    BASE_URL,
    create_pet,
    ensure_petstore_client,
    load_contract,
    validate_schema,
)

_fake = Faker()

_PET_REQUIRED_FIELDS = frozenset({"id", "name", "photoUrls"})


def _ensure_pet_id(context) -> None:
    """Create a pet and store its ID if context.pet_id has not been set."""
    if not getattr(context, "pet_id", None):
        pet = create_pet(context.client, _fake)
        context.pet_id = pet["id"]
        pet_id = context.pet_id
        context.cleanup.add(lambda: context.client.delete(f"{BASE_URL}/pet/{pet_id}"))
_PET_ALLOWED_FIELDS  = frozenset({"id", "name", "photoUrls", "status", "category", "tags"})
_PET_STATUS_ENUM     = frozenset({"available", "pending", "sold"})
# Minimal field set from a hypothetical older contract version
_OLDER_REQUIRED      = frozenset({"name", "photoUrls"})


# ---------------------------------------------------------------------------
# GIVEN
# ---------------------------------------------------------------------------

@given('pet status response')
def step_pet_status_response(context):
    ensure_petstore_client(context)
    r = context.client.get(f"{BASE_URL}/pet/findByStatus", params={"status": "available"})
    assert r.status_code == 200, f"Setup: findByStatus failed — {r.status_code}"
    pets = r.json()
    assert pets, "No pets returned for status=available; cannot validate status enum"
    context.response = r
    context.response_status = r.status_code
    context.pet_status_value = pets[0].get("status")


@given('existing pet response')
def step_existing_pet_response(context):
    ensure_petstore_client(context)
    _ensure_pet_id(context)
    r = context.client.get(f"{BASE_URL}/pet/{context.pet_id}")
    assert r.status_code == 200, f"Setup: get pet failed — {r.status_code}"
    context.response = r
    context.response_status = r.status_code
    context.pet_body = r.json()


@given('older API contract version')
def step_older_api_contract(context):
    ensure_petstore_client(context)
    context.older_required_fields = list(_OLDER_REQUIRED)


# ---------------------------------------------------------------------------
# WHEN
# ---------------------------------------------------------------------------

@when('user retrieves pet details')
def step_retrieve_pet_details(context):
    r = context.client.get(f"{BASE_URL}/pet/{context.pet_id}")
    context.response = r
    context.response_status = r.status_code
    assert r.status_code == 200, f"Expected 200, got {r.status_code} — {r.text[:200]}"


@when('latest API response is validated')
def step_validate_latest_response(context):
    _ensure_pet_id(context)
    r = context.client.get(f"{BASE_URL}/pet/{context.pet_id}")
    context.response = r
    context.response_status = r.status_code
    assert r.status_code == 200, f"Expected 200, got {r.status_code} — {r.text[:200]}"


# ---------------------------------------------------------------------------
# THEN
# ---------------------------------------------------------------------------

@then('response must contain all required fields')
def step_response_required_fields(context):
    body = context.response.json()
    missing = _PET_REQUIRED_FIELDS - set(body.keys())
    assert not missing, f"Required fields missing: {missing}"


@then('all field datatypes must match OpenAPI schema')
def step_field_datatypes_match(context):
    validate_schema(context.response.json(), load_contract("pet.v1"))


@then('status value should belong to allowed enum list')
def step_status_in_enum(context):
    status = getattr(context, "pet_status_value", None)
    assert status in _PET_STATUS_ENUM, (
        f"Status '{status}' not in allowed enum {_PET_STATUS_ENUM}"
    )


@then('response should not contain undocumented fields')
def step_no_undocumented_fields(context):
    body = getattr(context, "pet_body", None) or context.response.json()
    extra = set(body.keys()) - _PET_ALLOWED_FIELDS
    assert not extra, f"Undocumented fields in response: {extra}"


@then('backward compatibility should pass')
def step_backward_compatibility(context):
    body = context.response.json()
    required = getattr(context, "older_required_fields", list(_OLDER_REQUIRED))
    missing = [f for f in required if f not in body]
    assert not missing, (
        f"Backward compatibility broken — fields from older contract missing: {missing}"
    )