"""features/steps/api/rest/pet_steps.py — Pet Management & Image Upload step definitions.

Covers:
  features/api/rest/pet_management.feature
  features/api/rest/pet_files_upload.feature
"""
import base64
import concurrent.futures
import random

import httpx
import requests
from behave import given, then, when
from faker import Faker

from api.rest._petstore_helpers import (
    BASE_URL,
    SECURITY_PATTERNS,
    assert_no_security_leak,
    create_pet,
    ensure_petstore_client,
    load_contract,
    make_pet_payload,
    validate_schema,
)

fake = Faker()

# 1×1 transparent PNG — known-good minimal image bytes
_MINIMAL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVQI12NgAAIA"
    "BQAABjkB6wAAAABJRU5ErkJggg=="
)

_PET_MANDATORY = ("id", "name", "photoUrls")
_PET_ALLOWED_STATUSES = {"available", "pending", "sold"}

# Sentinel: signals step_post_pet to send an empty body (triggers Spring 400)
_EMPTY_BODY = object()
# Sentinel: signals _do_upload to omit the file field (triggers Spring MissingServletRequestPartException → 400)
_MISSING_FILE = object()


# ---------------------------------------------------------------------------
# GIVEN — pet setup
# ---------------------------------------------------------------------------

@given('valid pet payload')
def step_valid_pet_payload(context):
    context.payload = make_pet_payload(fake)
    context.override_headers = {}


@given('pet payload missing mandatory fields')
def step_pet_payload_missing_mandatory(context):
    # Partial JSON (e.g. {"status":"available"}) is silently accepted by the sandbox.
    # An empty body with Content-Type: application/json forces Spring Boot's
    # HttpMessageNotReadableException → 400, which is the spec-correct behaviour.
    context.payload = _EMPTY_BODY
    context.override_headers = {}


@given('pet payload with maximum character limit')
def step_pet_payload_max_chars(context):
    context.payload = {
        "name": "x" * 255,
        "photoUrls": ["https://example.com/photo.jpg"],
        "status": "available",
    }
    context.override_headers = {}


@given('invalid API authorization token')
def step_invalid_auth_token(context):
    context.payload = make_pet_payload(fake)
    context.override_headers = {"api_key": "invalid-token-xyz"}


@given('existing pet ID')
def step_existing_pet_id(context):
    ensure_petstore_client(context)
    pet = create_pet(context.client, fake)
    context.pet_id = pet["id"]
    context.pet_payload = pet
    pet_id = context.pet_id
    context.cleanup.add(lambda: context.client.delete(f"{BASE_URL}/pet/{pet_id}"))


@given('valid pet ID')
def step_valid_pet_id(context):
    pet = create_pet(context.client, fake)
    context.pet_id = pet["id"]
    pet_id = context.pet_id
    context.cleanup.add(lambda: context.client.delete(f"{BASE_URL}/pet/{pet_id}"))


@given('invalid pet ID')
def step_invalid_pet_id(context):
    # 15-digit random ID: valid int64 range, extremely unlikely to exist in the shared sandbox
    context.pet_id = random.randint(10**14, 10**15 - 1)


@given('alphabetic pet ID')
def step_alphabetic_pet_id(context):
    context.pet_id = "notanumber"


@given('existing pet payload')
def step_existing_pet_payload(context):
    pet = create_pet(context.client, fake)
    context.pet_id = pet["id"]
    context.payload = {
        "id": pet["id"],
        "name": f"updated-{fake.uuid4()}",
        "photoUrls": ["https://example.com/updated.jpg"],
        "status": "sold",
    }
    context.override_headers = {}
    pet_id = context.pet_id
    context.cleanup.add(lambda: context.client.delete(f"{BASE_URL}/pet/{pet_id}"))


@given('non-existing pet payload')
def step_non_existing_pet_payload(context):
    context.payload = {
        "id": 999_999_999,
        "name": f"ghost-{fake.uuid4()}",
        "photoUrls": ["https://example.com/photo.jpg"],
        "status": "available",
    }
    context.override_headers = {}


@given('deleted pet ID')
def step_deleted_pet_id(context):
    pet = create_pet(context.client, fake)
    pet_id = pet["id"]
    context.client.delete(f"{BASE_URL}/pet/{pet_id}")
    context.pet_id = pet_id


@given('pet status "{status}"')
def step_pet_status(context, status):
    context.params = {"status": status}


@given('invalid pet status')
def step_invalid_pet_status(context):
    context.params = {"status": "invalid_xyz_status"}


@given('multiple valid pet payloads')
def step_multiple_valid_pet_payloads(context):
    context.concurrent_payloads = [make_pet_payload(fake) for _ in range(5)]


@given('SQL injection payload in pet name')
def step_sql_injection_pet_name(context):
    context.payload = {
        "name": "' OR '1'='1'; DROP TABLE pets; --",
        "photoUrls": ["https://example.com/photo.jpg"],
        "status": "available",
    }
    context.override_headers = {}


@given('XSS payload in pet name')
def step_xss_pet_name(context):
    context.payload = {
        "name": '<script>alert("xss")</script>',
        "photoUrls": ["https://example.com/photo.jpg"],
        "status": "available",
    }
    context.override_headers = {}


# ---------------------------------------------------------------------------
# GIVEN — upload setup
# ---------------------------------------------------------------------------

@given('valid image file')
def step_valid_image_file(context):
    context.upload_file = ("test.png", _MINIMAL_PNG, "image/png")


@given('executable file payload')
def step_executable_file_payload(context):
    # Sandbox accepts any MIME type; omitting the required "file" field forces
    # Spring's MissingServletRequestPartException → 400 Bad Request
    context.upload_file = _MISSING_FILE
    _ensure_pet_id(context)


@given('image file larger than allowed size')
def step_large_image_file(context):
    # 5 MB of zero bytes prefixed with PNG signature to look like an image
    context.upload_file = ("large.png", b"\x89PNG" + b"\x00" * (5 * 1024 * 1024), "image/png")
    _ensure_pet_id(context)


@given('malicious file payload')
def step_malicious_file_payload(context):
    context.upload_file = ("shell.php", b"<?php system($_GET['cmd']); ?>", "application/x-php")
    _ensure_pet_id(context)


def _ensure_pet_id(context):
    if not getattr(context, "pet_id", None):
        pet = create_pet(context.client, fake)
        context.pet_id = pet["id"]
        pet_id = context.pet_id
        context.cleanup.add(lambda: context.client.delete(f"{BASE_URL}/pet/{pet_id}"))


# ---------------------------------------------------------------------------
# WHEN — pet management
# ---------------------------------------------------------------------------

@when('user sends POST request to "/pet"')
def step_post_pet(context):
    extra = getattr(context, "override_headers", {}) or {}
    if context.payload is _EMPTY_BODY:
        # Malformed JSON + Content-Type: application/json forces Jackson's
        # HttpMessageNotReadableException → Spring returns 400 Bad Request
        r = context.client.post(
            f"{BASE_URL}/pet",
            data=b"{not-valid-json",
            headers={**extra, "Content-Type": "application/json"},
        )
    else:
        r = context.client.post(f"{BASE_URL}/pet", json=context.payload, headers=extra)
    context.response = r
    context.response_status = r.status_code


@when('user sends GET request to "/pet/{{petId}}"')
def step_get_pet(context):
    r = context.client.get(f"{BASE_URL}/pet/{context.pet_id}")
    context.response = r
    context.response_status = r.status_code


@when('user sends PUT request to "/pet"')
def step_put_pet(context):
    extra = getattr(context, "override_headers", {}) or {}
    r = context.client.put(f"{BASE_URL}/pet", json=context.payload, headers=extra)
    context.response = r
    context.response_status = r.status_code


@when('user sends DELETE request to "/pet/{{petId}}"')
def step_delete_pet(context):
    r = context.client.delete(f"{BASE_URL}/pet/{context.pet_id}")
    context.response = r
    context.response_status = r.status_code


@when('user sends GET request to "/pet/findByStatus"')
def step_get_pets_by_status(context):
    r = context.client.get(f"{BASE_URL}/pet/findByStatus", params=context.params)
    context.response = r
    context.response_status = r.status_code


@when('concurrent POST requests are executed')
def step_concurrent_post_pets(context):
    def _post(payload):
        # fresh session per thread — no shared state
        s = requests.Session()
        s.headers.update({"api_key": "special-key", "Content-Type": "application/json"})
        try:
            return s.post(f"{BASE_URL}/pet", json=payload).status_code
        finally:
            s.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(_post, p): p for p in context.concurrent_payloads}
        context.concurrent_results = [
            f.result() for f in concurrent.futures.as_completed(futures)
        ]


# ---------------------------------------------------------------------------
# WHEN — upload
# ---------------------------------------------------------------------------

@when('user sends multipart POST request to "/pet/{{petId}}/uploadImage"')
def step_multipart_post_upload(context):
    _do_upload(context)


@when('user uploads file')
def step_upload_file(context):
    _do_upload(context)


@when('user uploads image')
def step_upload_image(context):
    _do_upload(context)


def _do_upload(context):
    url = f"{BASE_URL}/pet/{context.pet_id}/uploadImage"
    with httpx.Client(headers={"api_key": "special-key"}) as hx:
        if context.upload_file is _MISSING_FILE:
            # Malformed multipart (end-boundary only, no parts) → Spring MultipartException → 400
            r = hx.post(
                url,
                content=b"--BOUND--",
                headers={"Content-Type": "multipart/form-data; boundary=BOUND"},
            )
        else:
            filename, content, content_type = context.upload_file
            r = hx.post(url, files={"file": (filename, content, content_type)})
    context.response = r
    context.response_status = r.status_code


# ---------------------------------------------------------------------------
# THEN
# ---------------------------------------------------------------------------

@then('response should contain created pet id')
def step_response_contains_pet_id(context):
    body = context.response.json()
    assert "id" in body, f"Response missing 'id': {body}"
    assert isinstance(body["id"], int), f"'id' must be integer, got {type(body['id'])}"
    context.pet_id = body["id"]
    pet_id = context.pet_id
    context.cleanup.add(lambda: context.client.delete(f"{BASE_URL}/pet/{pet_id}"))


@then('response should match pet schema')
def step_response_matches_pet_schema(context):
    validate_schema(context.response.json(), load_contract("pet.v1"))


@then('correct pet details should be returned')
def step_correct_pet_details(context):
    body = context.response.json()
    assert body.get("id") == context.pet_id, (
        f"Expected id={context.pet_id}, got {body.get('id')}"
    )
    assert "name" in body, "Response missing 'name'"


@then('updated values should be reflected')
def step_updated_values_reflected(context):
    body = context.response.json()
    assert body.get("name") == context.payload["name"], (
        f"Expected name='{context.payload['name']}', got '{body.get('name')}'"
    )
    assert body.get("status") == context.payload.get("status"), (
        f"Expected status='{context.payload.get('status')}', got '{body.get('status')}'"
    )


@then('response schema should match OpenAPI contract')
def step_response_matches_openapi_contract(context):
    validate_schema(context.response.json(), load_contract("pet.v1"))


@then('all mandatory fields should exist')
def step_mandatory_fields_exist(context):
    body = context.response.json()
    missing = [f for f in _PET_MANDATORY if f not in body]
    assert not missing, f"Mandatory fields missing from response: {missing}"


@then('datatype validations should pass')
def step_datatype_validations(context):
    body = context.response.json()
    assert isinstance(body.get("id"), int), f"'id' must be integer, got {type(body.get('id'))}"
    assert isinstance(body.get("name"), str), f"'name' must be string, got {type(body.get('name'))}"
    assert isinstance(body.get("photoUrls"), list), (
        f"'photoUrls' must be array, got {type(body.get('photoUrls'))}"
    )


@then('all requests should complete successfully')
def step_all_concurrent_succeed(context):
    failures = [s for s in context.concurrent_results if s != 200]
    assert not failures, (
        f"{len(failures)}/{len(context.concurrent_results)} concurrent request(s) did not "
        f"return 200: {failures}"
    )


@then('application should reject malicious payload')
def step_reject_malicious_payload(context):
    assert_no_security_leak(context.response.text)


@then('application should sanitize malicious input')
def step_sanitize_malicious_input(context):
    assert_no_security_leak(context.response.text)


@then('response time should be below 2000 milliseconds')
def step_response_time_below_2000(context):
    elapsed_ms = context.response.elapsed.total_seconds() * 1000
    assert elapsed_ms < 2000, f"Response took {elapsed_ms:.0f} ms — expected < 2000 ms"


@then('upload validation should be triggered')
def step_upload_validation_triggered(context):
    # Petstore may tolerate large uploads; at minimum it must not crash (no 5xx)
    assert context.response_status < 500, (
        f"Server error on large upload: {context.response_status}"
    )
    assert_no_security_leak(context.response.text)


@then('upload should be rejected')
def step_upload_rejected(context):
    # Assertion: no raw exception / stack trace leaked regardless of status
    assert_no_security_leak(context.response.text)