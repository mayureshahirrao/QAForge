Feature: MySQL Country Table Validation
  As a database QA engineer
  I want to validate the country table schema and data integrity
  So that the master country data remains consistent

  Background:
    Given the MySQL database connection is established

  Scenario: Validate country table exists
    When I query metadata for table "country"
    Then the table "country" should exist

  Scenario: Validate country code uniqueness
    When I execute duplicate check on column "Code" in table "country"
    Then no duplicate records should exist

  Scenario: Validate continent enum values
    When I insert a country with invalid continent enum
    Then the insert operation should fail

  Scenario: Validate nullable IndepYear
    When I insert a country record with null "IndepYear"
    Then the insert operation should succeed

  Scenario: Validate mandatory Name field
    When I insert a country record with null "Name"
    Then the insert operation should fail