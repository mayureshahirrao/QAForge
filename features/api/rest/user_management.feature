@user @regression
Feature: User Management APIs

  Background:
    Given Swagger Petstore API is available

  @positive
  Scenario: Create user successfully
    Given valid user payload
    When user sends POST request to "/user"
    Then response status should be 200

  @positive
  Scenario: Create multiple users
    Given valid users list payload
    When user sends POST request to "/user/createWithList"
    Then response status should be 200

  @positive
  Scenario: Login successfully
    Given valid username and password
    When user sends GET request to "/user/login"
    Then response status should be 200
    And authentication token should be returned

  @negative
  Scenario: Login with invalid credentials
    Given invalid username and password
    When user sends GET request to "/user/login"
    Then response status should be 400

  @security
  Scenario: Login using SQL injection payload
    Given SQL injection username
    When user sends login request
    Then authentication should fail

  @positive
  Scenario: Retrieve user successfully
    Given existing username
    When user sends GET request to "/user/{username}"
    Then response status should be 200

  @negative
  Scenario: Retrieve non-existing user
    Given invalid username
    When user sends GET request to "/user/{username}"
    Then response status should be 404

  @positive
  Scenario: Update user successfully
    Given existing user payload
    When user sends PUT request to "/user/{username}"
    Then response status should be 200

  @negative
  Scenario: Update user with invalid payload
    Given invalid user payload
    When user sends PUT request to "/user/{username}"
    Then response status should be 400

  @positive
  Scenario: Delete existing user
    Given existing username
    When user sends DELETE request to "/user/{username}"
    Then response status should be 200

  @integration
  Scenario: Validate deleted user cannot login
    Given deleted username credentials
    When user sends login request
    Then authentication should fail