Feature: MySQL City-Country Referential Integrity
  As a database QA engineer
  I want to validate parent-child relationships
  So that orphan records are prevented

  Background:
    Given the MySQL database connection is established

  Scenario: Validate city references valid country
    When I insert a city with invalid CountryCode
    Then the insert operation should fail

  Scenario: Validate valid city-country relationship
    When I insert a city with valid CountryCode
    Then the insert operation should succeed

  Scenario: Validate delete restricted for parent country
    Given country code "IND" is referenced by city table
    When I delete country code "IND"
    Then the delete operation should fail

  Scenario: Validate orphan city records
    When I execute orphan validation query for city table
    Then no orphan records should exist