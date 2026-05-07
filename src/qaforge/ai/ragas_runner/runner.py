"""
qaforge.ai.ragas_runner.runner
==============================
RAG (Retrieval-Augmented Generation) evaluation using RAGAs.

Metrics:
- faithfulness                — answer is grounded in retrieved context
- answer_relevancy            — answer is relevant to the question
- context_precision           — retrieved context is on-topic for the question
- context_recall              — retrieved context covers ground-truth info

Usage in steps:
    runner = RagasRunner(cfg)
    result = runner.evaluate_single(question, answer, contexts, ground_truth)
    assert result.metrics["faithfulness"] >= cfg.ai.thresholds["faithfulness"]
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    answer_relevancy,
    context_precision,
    context_recall,
    faithfulness,
)

from qaforge.core.config_loader import Config
from qaforge.core.logger import get_logger

log = get_logger(__name__)


@dataclass
class RagasResult:
    metrics: Dict[str, float]      # name -> score
    thresholds: Dict[str, float]   # configured thresholds
    passed: bool                   # all metrics >= thresholds

    def fail_reason(self) -> str:
        bad = [
            f"{k}={self.metrics[k]:.3f} < {self.thresholds[k]:.3f}"
            for k in self.metrics
            if k in self.thresholds and self.metrics[k] < self.thresholds[k]
        ]
        return "; ".join(bad) or "ok"


class RagasRunner:
    DEFAULT_METRICS = [faithfulness, answer_relevancy, context_precision, context_recall]

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.thresholds = cfg.ai.thresholds

    def evaluate_single(
        self,
        question: str,
        answer: str,
        contexts: List[str],
        ground_truth: Optional[str] = None,
    ) -> RagasResult:
        return self.evaluate_batch(
            questions=[question],
            answers=[answer],
            contexts_list=[contexts],
            ground_truths=[ground_truth or ""],
        )

    def evaluate_batch(
        self,
        questions: List[str],
        answers: List[str],
        contexts_list: List[List[str]],
        ground_truths: List[str],
    ) -> RagasResult:
        ds = Dataset.from_dict(
            {
                "question": questions,
                "answer": answers,
                "contexts": contexts_list,
                "ground_truth": ground_truths,
            }
        )
        log.info(f"RAGAs evaluating {len(questions)} samples")
        result = evaluate(ds, metrics=self.DEFAULT_METRICS)
        # `result` is a dict-like; convert to plain floats (avg over batch)
        scores = {k: float(v) for k, v in result.to_pandas().mean(numeric_only=True).items()}
        passed = all(
            scores.get(k, 0.0) >= thr
            for k, thr in self.thresholds.items()
            if k in scores
        )
        return RagasResult(metrics=scores, thresholds=self.thresholds, passed=passed)
