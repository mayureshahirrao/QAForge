Feature: PostgreSQL Security Validation
  As a database QA engineer
  I want to validate database security
  So that unauthorized access is prevented

  Background:
    Given the PostgreSQL database connection is established

  Scenario: Prevent SQL injection
    When malicious SQL input is executed
    Then the database should reject the attack

  Scenario: Restrict payment table deletion
    When unauthorized user deletes payment records
    Then access should be denied

  Scenario: Validate sensitive column protection
    When non-admin user accesses password field
    Then access should be restricted

  Scenario: Validate audit logging
    When sensitive data is updated
    Then audit logs should capture the changes