Feature: PostgreSQL Performance Validation
  As a database QA engineer
  I want to validate database performance
  So that production scalability is ensured

  Background:
    Given the PostgreSQL database connection is established

  Scenario: Validate payment query performance
    When I query 10 million payment rows
    Then response time should remain within SLA

  Scenario: Validate index usage
    When I execute indexed customer query
    Then execution plan should use index scan

  Scenario: Validate pagination performance
    When paginated customer queries are executed
    Then response time should remain stable

  Scenario: Validate concurrent inserts
    When multiple bulk inserts run simultaneously
    Then deadlocks should not occur