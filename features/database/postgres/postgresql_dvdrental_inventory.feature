Feature: PostgreSQL Inventory Validation
  As a database QA engineer
  I want to validate inventory consistency
  So that stock tracking remains accurate

  Background:
    Given the PostgreSQL database connection is established

  Scenario: Validate inventory references film
    When I insert inventory with invalid film_id
    Then insertion should fail

  Scenario: Validate inventory creation
    When I insert valid inventory record
    Then insertion should succeed

  Scenario: Validate bulk inventory insertion
    When I insert 100000 inventory records
    Then performance should remain within SLA

  Scenario: Validate inventory deletion
    Given inventory is linked to rental
    When inventory is deleted
    Then deletion should fail
