@ui @smoke
Feature: User authentication
  As a registered user
  I want to log into the application
  So that I can access my dashboard

  Background:
    Given I am running against the "dev" environment
    And I open the login page

  Scenario: Successful login lands on dashboard
    Given a known user "alice"
    When I log in as "alice"
    Then I should land on the dashboard as "alice@example.com"

  Scenario: Wrong password shows an error
    When I log in with email "alice@example.com" and password "wrong-password"
    Then I should see the login error "Invalid credentials"
