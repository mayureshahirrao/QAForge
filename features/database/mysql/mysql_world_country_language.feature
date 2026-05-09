Feature: MySQL CountryLanguage Validation
  As a database QA engineer
  I want to validate language mappings
  So that multilingual data remains accurate

  Background:
    Given the MySQL database connection is established

  Scenario: Validate official language enum
    When I insert invalid enum value into "IsOfficial"
    Then the insert operation should fail

  Scenario: Validate percentage precision
    When I insert decimal percentage value
    Then the value should store accurately

  Scenario: Validate duplicate language mapping prevention
    When I insert duplicate country-language mapping
    Then the system should reject duplicates

  Scenario: Validate multilingual character support
    When I insert Unicode language values
    Then the data should persist correctly