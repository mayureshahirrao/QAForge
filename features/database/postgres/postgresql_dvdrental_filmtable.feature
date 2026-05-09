Feature: PostgreSQL Film Table Validation
  As a database QA engineer
  I want to validate film catalog data
  So that movie inventory remains accurate

  Background:
    Given the PostgreSQL database connection is established

  Scenario: Validate ARRAY datatype storage
    When I insert special_features array
    Then the array should store correctly

  Scenario: Validate USER-DEFINED rating enum
    When I insert invalid film rating
    Then the insert operation should fail

  Scenario: Validate fulltext search indexing
    When I perform fulltext search on film table
    Then relevant records should be returned

  Scenario: Validate mandatory title field
    When I insert film with null title
    Then the insert operation should fail

  Scenario: Validate replacement cost precision
    When I insert decimal replacement_cost
    Then the value should persist accurately