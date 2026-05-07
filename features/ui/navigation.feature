@ui @regression
Feature: Navigation and network interception

  Background:
    Given I am running against the "dev" environment
    And a known user "alice"
    And I open the login page
    When I log in as "alice"

  Scenario: Stub out the metrics endpoint and verify dashboard renders
    Given I record all network requests
    And I stub the endpoint "**/api/metrics**" with status 200 and JSON body
      """
      {"users": 100, "orders": 50, "revenue": 12345}
      """
    Then a request to "/api/metrics" should have been made
