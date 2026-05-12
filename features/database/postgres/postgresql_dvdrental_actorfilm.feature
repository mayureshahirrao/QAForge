Feature: PostgreSQL Film Actor Relationship Validation
  As a database QA engineer
  I want to validate many-to-many mappings
  So that actor-film relationships remain consistent

  Background:
    Given the PostgreSQL database connection is established

  @postgres
  Scenario: Insert valid film_actor mapping
    When I insert valid actor_id and film_id
    Then the mapping should be created

  @postgres
  Scenario: Prevent orphan film_actor mapping
    When I insert invalid actor_id
    Then foreign key validation should fail

  @postgres
  Scenario: Prevent duplicate film_actor mapping
    When duplicate mapping is inserted
    Then duplicate insertion should fail

  @postgres
  Scenario: Validate cascading delete behavior
    Given actor has mapped films
    When actor record is deleted
    Then relationship integrity should be maintained