Feature: PostgreSQL Reporting View Validation
  As a database QA engineer
  I want to validate reporting views
  So that analytics remain accurate

  Background:
    Given the PostgreSQL database connection is established

  Scenario: Validate sales_by_store aggregation
    When I calculate payment totals manually
    Then results should match sales_by_store view

  Scenario: Validate film_list aggregation
    When I fetch actors for a film
    Then film_list should display correct actor aggregation

  Scenario: Validate customer_list reporting data
    When customer address changes
    Then customer_list view should reflect latest data

  Scenario: Validate reporting query performance
    When reporting queries are executed
    Then execution time should remain within SLA