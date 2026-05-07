@api @websocket @regression
Feature: Real-time WebSocket notifications

  Background:
    Given I am running against the "dev" environment
    And I authenticate the WebSocket client with role "admin"

  Scenario: Subscribe to notifications and assert echo
    When I send a WebSocket message and expect 1 replies within 5 seconds
      """
      {"type": "ping", "id": "abc"}
      """
    Then the WebSocket reply count should be at least 1
    And the first WebSocket reply field "type" should equal "pong"

  Scenario: Stream live notifications for 3 seconds
    When I subscribe and stream for 3 seconds
      """
      {"type": "subscribe", "channel": "system.health"}
      """
    Then the WebSocket reply count should be at least 1
