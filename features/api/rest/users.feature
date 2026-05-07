@api @rest @regression
Feature: Users REST API

  Background:
    Given I am running against the "dev" environment
    And I authenticate the REST client with role "admin"

  Scenario: List users (pagination, contract validation)
    When I list users on page 1 with limit 20
    Then the response status should be 200
    And the response body matches the "users.list.v1" contract
    And the response should contain at least 1 items

  @no_prod
  Scenario: Create, fetch, patch a user
    Given a freshly generated user with role "viewer"
    When I create a user from the generated payload
    Then the response status should be 201
    And the response body matches the "user.v1" contract

    When I get the created user
    Then the response status should be 200

    When I patch the created user with
      """
      {"fullName": "Updated Name"}
      """
    Then the response status should be 200
    And the response field "fullName" should equal "Updated Name"

  @rbac
  Scenario Outline: Role-based access — viewers cannot create users
    Given I authenticate the REST client with role "<role>"
    And a freshly generated user with role "viewer"
    When I create a user from the generated payload
    Then the response status should be <status>

    Examples:
      | role   | status |
      | viewer | 403    |
      | editor | 201    |
      | admin  | 201    |
