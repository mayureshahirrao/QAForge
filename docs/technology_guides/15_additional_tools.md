# 15 — Additional Tools (DeepEval, RAGAs, Allure, Behavex, Tenacity, jsonschema)

This guide covers the remaining tools that sit alongside the protocol clients.

---

## 1. DeepEval — LLM evaluation

> **Source:** `src/qaforge/ai/deepeval_runner/runner.py`.

DeepEval treats LLM outputs as testable artefacts. Each metric scores `[0, 1]` against a configurable threshold.

| Metric                          | Question it answers                                                   |
| ------------------------------- | --------------------------------------------------------------------- |
| `AnswerRelevancyMetric`         | Is the answer relevant to the question?                               |
| `FaithfulnessMetric`            | Does the answer stick to the retrieved context (no hallucinations)?   |
| `HallucinationMetric`           | Does the answer invent facts not in the provided context?             |
| `BiasMetric`                    | Does the answer exhibit demographic, ideological, or other bias?      |
| `ToxicityMetric`                | Is the answer harmful, hateful, or unsafe?                            |
| `GEval` (custom)                | Any custom rubric: "Cites a source", "Stays under 100 words", etc.   |

Thresholds live in `cfg.ai.thresholds` (per-environment YAML). Override per call when needed:

```python
result = runner.answer_relevancy(input_text, output, threshold=0.85)
assert result.passed, result.reason
```

Each `MetricResult` carries `passed`, `score`, `reason`, `threshold` — wire them into reports for traceability.

**Cost note.** Every metric call invokes an LLM. Run AI suites less often than UI/API ones (nightly, not per commit) to keep spend bounded.

---

## 2. RAGAs — RAG pipeline evaluation

> **Source:** `src/qaforge/ai/ragas_runner/runner.py`.

Where DeepEval evaluates a single LLM call, RAGAs evaluates a full **retrieval-augmented generation** pipeline. Inputs:

- `question`
- `answer`
- `contexts` — what the retriever returned
- `ground_truth` — what the answer *should* have been

Default metrics:

- `faithfulness` — answer is grounded in the retrieved contexts.
- `answer_relevancy` — answer addresses the question.
- `context_precision` — retrieved contexts are on-topic for the question.
- `context_recall` — retrieved contexts cover the ground-truth information.

The `RagasResult` aggregates per-metric scores and a `passed` boolean (all metrics ≥ thresholds). Failures explain *why* via `result.fail_reason()`:

```
faithfulness=0.612 < 0.800; context_recall=0.491 < 0.700
```

Use this in incident reviews when retrieval changes ship.

---

## 3. Allure — rich HTML reports

> **Source:** `src/qaforge/reporting/allure_helpers.py`. Wired in `behave.ini` (`[behave.formatters]`) and via `scripts/run.sh`.

Allure produces an interactive HTML report with timelines, history, attachments, and tag/feature/severity filters. QAForge attaches:

- **Screenshots** — full-page PNG on every UI failure (`after_step` hook).
- **Videos** — full-scenario WebM (`after_scenario`).
- **Traces** — Playwright trace zip; open with `playwright show-trace`.
- **Logs / JSON** — per-step text or JSON via `attach_text` / `attach_json`.

Generate the HTML report:

```bash
allure generate reports/allure/results -o reports/allure/report --clean
allure serve  reports/allure/results          # opens in browser
```

To label scenarios in Allure (for ownership dashboards):

```python
import allure
@given('I am on the team payments suite')
def step(context):
    allure.dynamic.label("owner", "team-payments")
    allure.dynamic.severity("critical")
```

---

## 4. Behavex — parallel Behave

> **Source:** Used by `scripts/run.sh`. CLI: `behavex --parallel-processes N --parallel-scheme scenario|feature`.

Behavex shards Behave scenarios across worker processes. Each worker owns a private Playwright browser and its own DB connections — no cross-process state leakage.

- **`--parallel-scheme scenario`** — finest grain; ideal when scenarios are roughly equal in cost.
- **`--parallel-scheme feature`** — coarser; good when scenarios share heavy in-feature setup.
- **`--parallel-processes N`** — keep N ≤ CPU count for CPU-bound suites; can go higher for I/O-bound (API/DB) ones.

Behavex consumes Behave's `behave.ini`, so the same configuration works for both serial and parallel runs.

---

## 5. Tenacity — retries done right

> **Source:** `src/qaforge/core/retry.py`.

Use the `retry_on` decorator only when an operation is genuinely flaky for environmental reasons (network, eventual consistency). Don't use it to paper over UI flakes — that's what Playwright's `expect()` is for.

```python
from qaforge.core.retry import retry_on
import httpx

@retry_on(exceptions=(httpx.TimeoutException, httpx.NetworkError), attempts=3, min_wait=1, max_wait=5)
def fetch_metrics():
    return context.rest.get("/metrics")
```

Built on `tenacity` — exponential backoff, configurable max wait, transparent re-raise after the last attempt. Logs every retry at WARNING.

---

## 6. jsonschema — contract validation

> **Source:** `src/qaforge/api/contract_validator.py`. Schemas in `test_data/static/contracts/`.

Draft 2020-12 validation. Schemas can reference each other via `$ref`/`$id`:

```json
{
  "$id": "users.list.v1",
  "type": "object",
  "properties": {
    "items": { "type": "array", "items": { "$ref": "user.v1" } }
  }
}
```

`validate_against_contract(payload, "users.list.v1")` walks every error and raises a `ValidationError` listing JSON pointers:

```
Contract users.list.v1 violated:
  - ['items', 0, 'role']: 'guest' is not one of ['admin', 'editor', 'viewer']
  - ['total']: 'forty-two' is not of type 'integer'
```

Treat schema files as a public API — version them (`v1`, `v2`) and never break compatibility silently.

---

## 7. Pydantic — runtime validation of internal models

> **Source:** `src/qaforge/core/config_loader.py`.

We use Pydantic v2 to validate the loaded YAML config. The benefit isn't just safety — it's **IDE typing**: `cfg.databases.postgres.port` autocompletes and is statically int.

When you add a new config key, declare it in the right Pydantic model. Skipping this leaves the value accessible only via raw dict lookup, which sidesteps validation.

---

## 8. python-dotenv — local secret loading

`load_dotenv(ROOT / ".env", override=False)` is called at import time in `config_loader.py`. Local devs put creds in `.env` (gitignored); CI sets them via secrets manager. Either way, `os.environ.get("PG_PASSWORD")` resolves correctly.

---

## 9. Rich — pretty CLI output

`rich==13.9.2` is included for ad-hoc CLI scripts (e.g. seed runners, custom diagnostics). It's not used in the test path itself — loguru handles that.
