@db @regression
Feature: Cross-database persistence and consistency

  Background:
    Given I am running against the "dev" environment

  @postgres
  Scenario: REST creation persists in Postgres
    Given I authenticate the REST client with role "admin"
    And a freshly generated user with role "viewer"
    And I cleanup Postgres rows in "users" where email = '{user.email}'
    When I create a user from the generated payload
    Then the response status should be 201
    And Postgres table "users" should have 1 rows where email = '{user.email}'

  @mysql
  Scenario: Audit log written to MySQL
    Given I authenticate the REST client with role "admin"
    When I list users on page 1 with limit 5
    Then MySQL table "audit_log" should have 1 rows where action = 'users.list'

  @mongo
  Scenario: User profile document exists in Mongo
    Then Mongo collection "user_profiles" should contain a doc with field "email" equal to "alice@example.com"

  @dynamo
  Scenario: Session token stored in DynamoDB
    Then Dynamo table "sessions" should contain item with key "user_id"="u-123"
