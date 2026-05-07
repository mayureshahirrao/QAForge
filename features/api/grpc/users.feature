@api @grpc @regression
Feature: Users gRPC service

  Background:
    Given I am running against the "dev" environment
    And I authenticate the gRPC client with role "admin"

  Scenario: Unary GetUser
    When I call GetUser with id "u-123"
    Then the gRPC user response email should equal "alice@example.com"

  Scenario: Server streaming ListUsers
    When I call ListUsers (server streaming) with page 1 and limit 10
    Then the gRPC server stream should contain at least 1 users
