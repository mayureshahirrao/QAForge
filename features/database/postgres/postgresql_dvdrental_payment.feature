Feature: PostgreSQL Payment Transaction Validation
  As a database QA engineer
  I want to validate payment transactions
  So that financial consistency is maintained

  Background:
    Given the PostgreSQL database connection is established

  Scenario: Insert valid payment
    When I insert valid payment details
    Then the payment should be created successfully

  Scenario: Prevent negative payment amount
    When I insert payment with negative amount
    Then the insert operation should fail

  Scenario: Validate payment customer relationship
    When I insert payment with invalid customer_id
    Then foreign key validation should fail

  Scenario: Validate payment timestamp
    When I create payment record
    Then payment_date should contain valid timestamp

  Scenario: Validate payment rollback
    Given payment transaction has started
    When rollback is executed
    Then no payment record should persist