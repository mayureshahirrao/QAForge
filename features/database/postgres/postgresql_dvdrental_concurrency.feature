Feature: PostgreSQL Rental Concurrency Validation
  As a database QA engineer
  I want to validate concurrent rental operations
  So that duplicate rentals are prevented

  Background:
    Given the PostgreSQL database connection is established

  Scenario: Concurrent rental booking for same inventory
    Given inventory item is available
    When two users attempt simultaneous rental
    Then only one transaction should succeed

  Scenario: Validate rental foreign keys
    When I insert rental with invalid inventory_id
    Then the insert operation should fail

  Scenario: Validate rental return date
    When return_date is earlier than rental_date
    Then validation should fail

  Scenario: Validate rental update timestamp
    When rental record is updated
    Then last_update should refresh automatically