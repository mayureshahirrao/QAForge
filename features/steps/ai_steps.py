"""features/steps/ai_steps.py — DeepEval + RAGAs step definitions."""
import json

from behave import given, then, when

from qaforge.ai.deepeval_runner.runner import DeepEvalRunner
from qaforge.ai.ragas_runner.runner import RagasRunner


@given('an AI evaluator is initialised')
def step_ai_init(context):
    context.deep = DeepEvalRunner(context.cfg)
    context.rag = RagasRunner(context.cfg)


@when('the LLM is asked')
def step_ai_ask(context):
    context.llm_input = context.text


@when('the LLM responds with')
def step_ai_response(context):
    context.llm_output = context.text


@when('the retrieved context is')
def step_ai_context(context):
    context.llm_context = json.loads(context.text)  # list[str]


@when('the ground truth is')
def step_ai_ground_truth(context):
    context.llm_ground_truth = context.text


# ---------- DeepEval assertions ----------
@then('the answer relevancy score should pass')
def step_relevancy(context):
    r = context.deep.answer_relevancy(context.llm_input, context.llm_output)
    assert r.passed, f"AnswerRelevancy {r.score:.3f} < {r.threshold:.3f}: {r.reason}"


@then('the faithfulness score should pass')
def step_faithfulness(context):
    r = context.deep.faithfulness(context.llm_input, context.llm_output, context.llm_context)
    assert r.passed, f"Faithfulness {r.score:.3f} < {r.threshold:.3f}: {r.reason}"


@then('the response should be free of hallucinations')
def step_no_hallucinations(context):
    r = context.deep.hallucination(context.llm_input, context.llm_output, context.llm_context)
    assert r.passed, f"Hallucination={r.score:.3f}: {r.reason}"


@then('the response should be non-toxic and unbiased')
def step_safe(context):
    t = context.deep.toxicity(context.llm_input, context.llm_output)
    b = context.deep.bias(context.llm_input, context.llm_output)
    assert t.passed and b.passed, f"toxicity={t.score:.3f} bias={b.score:.3f}"


@then('the custom criterion "{name}" with rubric "{criteria}" should pass')
def step_geval(context, name, criteria):
    r = context.deep.custom_geval(
        name=name, criteria=criteria,
        input_text=context.llm_input,
        actual_output=context.llm_output,
        expected_output=getattr(context, "llm_ground_truth", None),
    )
    assert r.passed, f"{r.name}={r.score:.3f}: {r.reason}"


# ---------- RAGAs ----------
@then('the RAG pipeline should pass all metrics')
def step_rag_pass(context):
    res = context.rag.evaluate_single(
        question=context.llm_input,
        answer=context.llm_output,
        contexts=context.llm_context,
        ground_truth=getattr(context, "llm_ground_truth", None),
    )
    assert res.passed, f"RAG metrics failed: {res.fail_reason()} | scores={res.metrics}"
