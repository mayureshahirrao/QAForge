@ai @regression
Feature: LLM and RAG quality gates

  Background:
    Given I am running against the "dev" environment
    And an AI evaluator is initialised

  Scenario: Plain LLM response is relevant, safe, and unbiased
    When the LLM is asked
      """
      What is the capital of France?
      """
    And the LLM responds with
      """
      The capital of France is Paris.
      """
    Then the answer relevancy score should pass
    And the response should be non-toxic and unbiased

  Scenario: RAG response is faithful to retrieved context
    When the LLM is asked
      """
      What is QAForge built on?
      """
    And the LLM responds with
      """
      QAForge is built on Behave for BDD, Playwright for UI testing,
      and supports REST, GraphQL, gRPC, WebSocket, and async APIs.
      """
    And the retrieved context is
      """
      ["QAForge uses Behave for BDD orchestration.",
       "Playwright drives all UI scenarios.",
       "Supported API protocols include REST, GraphQL, gRPC, WebSocket, and async (Kafka)."]
      """
    Then the faithfulness score should pass
    And the response should be free of hallucinations
    And the RAG pipeline should pass all metrics

  Scenario: Custom rubric — answer should cite at least one source
    When the LLM is asked
      """
      Give me a one-sentence summary of the QAForge framework with a source.
      """
    And the LLM responds with
      """
      QAForge is a production-grade BDD test framework (source: docs/manuals/framework_manual.md).
      """
    Then the custom criterion "CitesSource" with rubric "The answer must cite at least one source in parentheses" should pass
