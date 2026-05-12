@pet @regression
Feature: Pet Management APIs

  Background:
    Given Swagger Petstore API is available
    And valid request headers are configured

  @smoke @positive
  Scenario: Create pet successfully
    Given valid pet payload
    When user sends POST request to "/pet"
    Then response status should be 200
    And response should contain created pet id
    And response should match pet schema

  @negative
  Scenario: Create pet with missing mandatory fields
    Given pet payload missing mandatory fields
    When user sends POST request to "/pet"
    Then response status should be 400

  @boundary
  Scenario: Create pet with maximum allowed name length
    Given pet payload with maximum character limit
    When user sends POST request to "/pet"
    Then response status should be 200

  @security
  Scenario: Create pet using invalid authorization
    Given invalid API authorization token
    When user sends POST request to "/pet"
    Then response status should be 401

  @contract
  Scenario: Validate create pet response contract
    Given valid pet payload
    When user sends POST request to "/pet"
    Then response schema should match OpenAPI contract
    And all mandatory fields should exist
    And datatype validations should pass

  @positive
  Scenario: Retrieve pet by valid ID
    Given existing pet ID
    When user sends GET request to "/pet/{petId}"
    Then response status should be 200
    And correct pet details should be returned

  @negative
  Scenario: Retrieve pet with invalid ID
    Given invalid pet ID
    When user sends GET request to "/pet/{petId}"
    Then response status should be 404

  @negative
  Scenario: Retrieve pet using alphabetic pet ID
    Given alphabetic pet ID
    When user sends GET request to "/pet/{petId}"
    Then response status should be 400

  @positive
  Scenario: Update existing pet successfully
    Given existing pet payload
    When user sends PUT request to "/pet"
    Then response status should be 200
    And updated values should be reflected

  @negative
  Scenario: Update non-existing pet
    Given non-existing pet payload
    When user sends PUT request to "/pet"
    Then response status should be 404

  @positive
  Scenario: Delete existing pet
    Given existing pet ID
    When user sends DELETE request to "/pet/{petId}"
    Then response status should be 200

  @integration
  Scenario: Validate deleted pet cannot be retrieved
    Given deleted pet ID
    When user sends GET request to "/pet/{petId}"
    Then response status should be 404

  @positive
  Scenario Outline: Find pets by status
    Given pet status "<status>"
    When user sends GET request to "/pet/findByStatus"
    Then response status should be 200

    Examples:
      | status    |
      | available |
      | pending   |
      | sold      |

  @negative
  Scenario: Find pets using invalid status
    Given invalid pet status
    When user sends GET request to "/pet/findByStatus"
    Then response status should be 400

  @performance
  Scenario: Validate pet retrieval response time
    Given existing pet ID
    When user sends GET request to "/pet/{petId}"
    Then response time should be below 2000 milliseconds

  @resilience
  Scenario: Validate concurrent pet creation
    Given multiple valid pet payloads
    When concurrent POST requests are executed
    Then all requests should complete successfully

  @security
  Scenario: Validate SQL injection payload handling
    Given SQL injection payload in pet name
    When user sends POST request to "/pet"
    Then application should reject malicious payload

  @security
  Scenario: Validate XSS payload handling
    Given XSS payload in pet name
    When user sends POST request to "/pet"
    Then application should sanitize malicious input