"""features/steps/api/rest/store_steps.py — Petstore Store Order step definitions.

Covers:
  features/api/rest/pet_store_orders.feature
"""
from behave import given, then, when

from api.rest._petstore_helpers import (
    BASE_URL,
    create_order,
    load_contract,
    validate_schema,
)


# ---------------------------------------------------------------------------
# GIVEN
# ---------------------------------------------------------------------------

@given('valid store order payload')
def step_valid_order_payload(context):
    context.payload = {
        "petId": 1,
        "quantity": 2,
        "status": "placed",
        "complete": False,
    }


@given('order payload with invalid quantity')
def step_invalid_quantity_payload(context):
    context.payload = {
        "petId": 1,
        "quantity": -1,
        "status": "placed",
        "complete": False,
    }


@given('existing order ID')
def step_existing_order_id(context):
    order = create_order(context.client)
    context.order_id = order["id"]
    order_id = context.order_id
    context.cleanup.add(lambda: context.client.delete(f"{BASE_URL}/store/order/{order_id}"))


@given('invalid order ID')
def step_invalid_order_id(context):
    context.order_id = 999_999_999


# ---------------------------------------------------------------------------
# WHEN
# ---------------------------------------------------------------------------

@when('user sends POST request to "/store/order"')
def step_post_order(context):
    r = context.client.post(f"{BASE_URL}/store/order", json=context.payload)
    context.response = r
    context.response_status = r.status_code


@when('user sends GET request to "/store/order/{{orderId}}"')
def step_get_order(context):
    r = context.client.get(f"{BASE_URL}/store/order/{context.order_id}")
    context.response = r
    context.response_status = r.status_code


@when('user sends DELETE request to "/store/order/{{orderId}}"')
def step_delete_order(context):
    r = context.client.delete(f"{BASE_URL}/store/order/{context.order_id}")
    context.response = r
    context.response_status = r.status_code


@when('user sends GET request to "/store/inventory"')
def step_get_inventory(context):
    r = context.client.get(f"{BASE_URL}/store/inventory")
    context.response = r
    context.response_status = r.status_code


# ---------------------------------------------------------------------------
# THEN
# ---------------------------------------------------------------------------

@then('order should be created successfully')
def step_order_created_successfully(context):
    body = context.response.json()
    assert "id" in body, f"Response missing 'id': {body}"
    assert isinstance(body["id"], int), f"'id' must be integer, got {type(body['id'])}"
    context.order_id = body["id"]
    order_id = context.order_id
    context.cleanup.add(lambda: context.client.delete(f"{BASE_URL}/store/order/{order_id}"))


@then('response schema should match contract')
def step_inventory_schema(context):
    body = context.response.json()
    # Inventory is a map of status→count; all values must be integers
    assert isinstance(body, dict), f"Expected dict for inventory, got {type(body)}"
    bad = {k: v for k, v in body.items() if not isinstance(v, int)}
    assert not bad, f"Non-integer inventory values: {bad}"