"""
qaforge.ai.deepeval_runner.runner
=================================
LLM evaluation using DeepEval. Wraps DeepEval's metric API to provide a
simple façade that step definitions can call.

Supported metrics out-of-the-box (extend as needed):
- AnswerRelevancyMetric
- FaithfulnessMetric
- HallucinationMetric
- BiasMetric
- ToxicityMetric
- GEval (custom criteria)

Each method returns a `MetricResult` with `passed`, `score`, `reason`, so
tests can assert against thresholds defined per environment in YAML.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from deepeval.metrics import (
    AnswerRelevancyMetric,
    BiasMetric,
    FaithfulnessMetric,
    GEval,
    HallucinationMetric,
    ToxicityMetric,
)
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

from qaforge.core.config_loader import Config
from qaforge.core.logger import get_logger

log = get_logger(__name__)


@dataclass
class MetricResult:
    name: str
    passed: bool
    score: float
    reason: str
    threshold: float


class DeepEvalRunner:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.model = cfg.ai.llm_model
        self.thresholds = cfg.ai.thresholds

    def _build_case(self, input_text: str, actual_output: str,
                    expected_output: Optional[str] = None,
                    retrieval_context: Optional[List[str]] = None,
                    context: Optional[List[str]] = None) -> LLMTestCase:
        return LLMTestCase(
            input=input_text,
            actual_output=actual_output,
            expected_output=expected_output,
            retrieval_context=retrieval_context,
            context=context,
        )

    # ---------- metrics ----------
    def answer_relevancy(self, input_text: str, actual_output: str,
                         threshold: Optional[float] = None) -> MetricResult:
        thr = threshold if threshold is not None else self.thresholds.get("answer_relevancy", 0.75)
        m = AnswerRelevancyMetric(threshold=thr, model=self.model, include_reason=True)
        case = self._build_case(input_text, actual_output)
        m.measure(case)
        return MetricResult("AnswerRelevancy", m.is_successful(), m.score, m.reason, thr)

    def faithfulness(self, input_text: str, actual_output: str, retrieval_context: List[str],
                     threshold: Optional[float] = None) -> MetricResult:
        thr = threshold if threshold is not None else self.thresholds.get("faithfulness", 0.80)
        m = FaithfulnessMetric(threshold=thr, model=self.model, include_reason=True)
        case = self._build_case(input_text, actual_output, retrieval_context=retrieval_context)
        m.measure(case)
        return MetricResult("Faithfulness", m.is_successful(), m.score, m.reason, thr)

    def hallucination(self, input_text: str, actual_output: str, context: List[str],
                      threshold: float = 0.3) -> MetricResult:
        # NB: lower is better — DeepEval flips the comparison via include_reason
        m = HallucinationMetric(threshold=threshold, model=self.model, include_reason=True)
        case = self._build_case(input_text, actual_output, context=context)
        m.measure(case)
        return MetricResult("Hallucination", m.is_successful(), m.score, m.reason, threshold)

    def bias(self, input_text: str, actual_output: str, threshold: float = 0.3) -> MetricResult:
        m = BiasMetric(threshold=threshold, model=self.model, include_reason=True)
        case = self._build_case(input_text, actual_output)
        m.measure(case)
        return MetricResult("Bias", m.is_successful(), m.score, m.reason, threshold)

    def toxicity(self, input_text: str, actual_output: str, threshold: float = 0.3) -> MetricResult:
        m = ToxicityMetric(threshold=threshold, model=self.model, include_reason=True)
        case = self._build_case(input_text, actual_output)
        m.measure(case)
        return MetricResult("Toxicity", m.is_successful(), m.score, m.reason, threshold)

    def custom_geval(self, name: str, criteria: str, input_text: str, actual_output: str,
                     expected_output: Optional[str] = None, threshold: float = 0.7) -> MetricResult:
        m = GEval(
            name=name,
            criteria=criteria,
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT,
                               LLMTestCaseParams.EXPECTED_OUTPUT],
            threshold=threshold,
            model=self.model,
        )
        case = self._build_case(input_text, actual_output, expected_output=expected_output)
        m.measure(case)
        return MetricResult(f"GEval[{name}]", m.is_successful(), m.score, m.reason, threshold)
