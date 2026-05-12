@store @regression
Feature: Store Order APIs

  Background:
    Given Swagger Petstore API is available

  @positive
  Scenario: Place store order successfully
    Given valid store order payload
    When user sends POST request to "/store/order"
    Then response status should be 200
    And order should be created successfully

  @negative
  Scenario: Place order with invalid quantity
    Given order payload with invalid quantity
    When user sends POST request to "/store/order"
    Then response status should be 400

  @positive
  Scenario: Retrieve order successfully
    Given existing order ID
    When user sends GET request to "/store/order/{orderId}"
    Then response status should be 200

  @negative
  Scenario: Retrieve non-existing order
    Given invalid order ID
    When user sends GET request to "/store/order/{orderId}"
    Then response status should be 404

  @positive
  Scenario: Delete existing order
    Given existing order ID
    When user sends DELETE request to "/store/order/{orderId}"
    Then response status should be 200

  @contract
  Scenario: Validate inventory response contract
    When user sends GET request to "/store/inventory"
    Then response schema should match contract