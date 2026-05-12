@upload @regression
Feature: Pet Image Upload APIs

  Background:
    Given Swagger Petstore API is available

  @positive
  Scenario: Upload valid pet image
    Given valid pet ID
    And valid image file
    When user sends multipart POST request to "/pet/{petId}/uploadImage"
    Then response status should be 200

  @negative
  Scenario: Upload unsupported file type
    Given executable file payload
    When user uploads file
    Then response status should be 400

  @boundary
  Scenario: Upload large image file
    Given image file larger than allowed size
    When user uploads image
    Then upload validation should be triggered

  @security
  Scenario: Upload malicious file
    Given malicious file payload
    When user uploads file
    Then upload should be rejected