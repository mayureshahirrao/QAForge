@ui @regression
Feature: Form submission with attachments and iframe captcha

  Background:
    Given I am running against the "dev" environment
    And a known user "alice"
    And I open the login page
    When I log in as "alice"

  @no_prod
  Scenario: Submit a complete form and export PDF
    Given I open the form page
    When I fill the form with title "Q4 Report", description "End-of-year analytics", category "Finance", attachment "test_data/static/sample.pdf"
    And I confirm the captcha checkbox
    And I submit the form
    Then a success toast should be visible
    When I export the form as PDF to "reports/custom/exports/q4_export.pdf"
    Then the exported file should exist and be non-empty
