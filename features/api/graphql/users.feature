@api @graphql @regression
Feature: Users GraphQL API

  Background:
    Given I am running against the "dev" environment
    And I authenticate the GraphQL client with role "admin"

  Scenario: Schema introspection
    Then the GraphQL schema should expose query, mutation, and subscription roots

  Scenario: List users via query
    When I run the listUsers query with page 1 and limit 10
    Then the GraphQL listUsers total should be at least 1

  @no_prod
  Scenario: Create then fetch a user via mutation
    When I create a user via GraphQL mutation with
      """
      {
        "email": "gql.user@example.com",
        "fullName": "GQL User",
        "role": "viewer"
      }
      """
    And I fetch the created user via GraphQL
    Then the GraphQL response field "user.email" should equal "gql.user@example.com"
