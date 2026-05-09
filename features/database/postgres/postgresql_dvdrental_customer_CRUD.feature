Feature: PostgreSQL Customer CRUD Validation
  As a database QA engineer
  I want to validate customer transactions
  So that customer data integrity is maintained

  Background:
    Given the PostgreSQL database connection is established

  Scenario: Insert valid customer
    When I insert a valid customer record
    Then the insert operation should succeed

  Scenario: Insert customer with invalid address
    When I insert customer with invalid address_id
    Then the insert operation should fail

  Scenario: Validate mandatory customer first name
    When I insert customer with null first_name
    Then the insert operation should fail

  Scenario: Update customer email
    Given customer record exists
    When I update customer email
    Then the update operation should succeed

  Scenario: Delete customer with rental history
    Given customer has rental records
    When I delete the customer
    Then the delete operation should fail