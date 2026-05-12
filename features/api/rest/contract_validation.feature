@contract
Feature: OpenAPI Contract Validation

  Scenario: Validate required fields in pet response
    Given existing pet ID
    When user retrieves pet details
    Then response must contain all required fields

  Scenario: Validate datatype consistency
    Given existing pet ID
    When user retrieves pet details
    Then all field datatypes must match OpenAPI schema

  Scenario: Validate enum values
    Given pet status response
    Then status value should belong to allowed enum list

  Scenario: Validate no unexpected properties exist
    Given existing pet response
    Then response should not contain undocumented fields

  Scenario: Validate backward compatibility
    Given older API contract version
    When latest API response is validated
    Then backward compatibility should pass 