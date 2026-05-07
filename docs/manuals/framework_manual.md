# QAForge — Framework Manual

This manual is the canonical, file-by-file reference for the QAForge codebase. For protocol-specific deep dives see `docs/technology_guides/`.

> **Reading order suggestion:** §1 architecture overview → §2 lifecycle → §3 file-by-file → relevant technology guide.

---

## 1. Architecture overview

QAForge is layered top-to-bottom:

```
features/*.feature  ──►  features/steps/*_steps.py
                                │
                                ▼
                         src/qaforge/
                                │
        ┌───────┬──────────┬────┴─────┬─────────┬─────────┐
        ▼       ▼          ▼          ▼         ▼         ▼
       core   pages       api      database    ai     reporting
                       (5 protos) (4 engines) (2 evals)
                                │
                                ▼
                          features/environment.py
                  (provisions clients per scenario)
```

**Two invariants the codebase enforces:**

1. **Protocol & engine isolation.** Removing `src/qaforge/api/grpc/` should never break REST, GraphQL, WebSocket, Kafka, or any DB code. The same is true for any DB folder. Steps that need a protocol are tagged accordingly so `environment.py` only provisions what's needed.
2. **Step files contain glue, not logic.** All business behaviour lives in page objects, API clients, or DB clients. Step files only translate Gherkin to method calls and assertions.

---

## 2. Lifecycle (Behave hooks)

Defined in `features/environment.py`:

| Hook              | Responsibility                                                                                  |
| ----------------- | ----------------------------------------------------------------------------------------------- |
| `before_all`      | Configure logging; load typed config; initialise reporter; start Playwright (one per worker).   |
| `before_feature`  | Create per-feature output directory.                                                            |
| `before_scenario` | Skip `@no_prod` in prod; create cleanup registry; provision clients matching scenario tags.     |
| `before_step`     | Stamp the step start time.                                                                      |
| `after_step`      | Compute step duration; on failure, capture screenshot and attach to Allure.                     |
| `after_scenario`  | Stop trace, save video, run cleanups (LIFO), retry once on failure, append Extent record.       |
| `after_feature`   | Reserved for symmetry; currently no-op.                                                         |
| `after_all`       | Finalise Extent JSON; render the custom HTML dashboard; stop Playwright.                        |

---

## 3. File-by-file documentation

### 3.1  Top-level

| File              | Purpose                                                                  |
| ----------------- | ------------------------------------------------------------------------ |
| `pyproject.toml`  | Build metadata; declares `src/` as the package root.                     |
| `requirements.txt`| Pinned production dependencies. Update with intent — no auto-bumps in CI.|
| `behave.ini`      | Behave runtime config: formatters (Allure + JUnit + pretty), logging level, default userdata (`env`, `browser`, `headless`, `parallel_workers`, `retry_failed`). |
| `.env.example`    | Secrets template. Copy to `.env`; never commit `.env`.                   |
| `.gitignore`      | Excludes virtualenvs, generated reports, logs, gRPC stubs.               |
| `scripts/run.sh`  | Convenience wrapper around `behavex` for the standard suites.            |
| `scripts/gen_grpc.sh` | Regenerates Python stubs from `proto/*.proto`.                       |

### 3.2  Configuration

#### `config/environments/dev.yaml` / `staging.yaml` / `prod.yaml`
**Purpose:** environment-specific URLs, timeouts, DB hosts, AI thresholds.
**Role:** loaded by `qaforge.core.config_loader`; chosen by `-D env=<name>` or `QAFORGE_ENV`.
**Schema:** described by Pydantic models in `config_loader.py` — invalid YAML fails fast at start-up.
**Notable keys:**
- `ui.trace`: `off | on | retain-on-failure`. We use `retain-on-failure` everywhere except prod.
- `ui.record_video`: full-scenario WebM video (attached to Allure on failure).
- `ai.thresholds`: minimum scores for DeepEval and RAGAs metrics.
- `read_only` (prod only): toggles the `@no_prod` guard in `before_scenario`.

#### `config/tags.json`
**Purpose:** declares the named suites (smoke / regression / ui / api / db / ai) and their default parallel worker counts.
**Role:** consumed by `scripts/run.sh` to map a suite name to a tag expression.

### 3.3  Core (`src/qaforge/core/`)

#### `config_loader.py`
**Purpose:** load YAML for the active environment and validate it through Pydantic.
**Methods:**
- `load_config(behave_userdata=None) -> Config` — main entry point. Resolves env from userdata → env var → `dev`. Reads `<env>.yaml`, validates, returns the typed `Config`.
- `secret(env_var, default=None) -> str` — fetches a secret from the environment, raising if absent and no default.
**Why typed?** Misnaming a key (`base_uri` instead of `base_url`) explodes at framework start, not 30 minutes into a regression run.

#### `browser_factory.py`
**Purpose:** centralise Playwright lifecycle so step authors never call `sync_playwright()` directly.
**Class:** `BrowserFactory(cfg, browser_name, headless)`.
**Methods:**
- `start()` / `stop()` — open and close the Playwright runtime + browser. Called once per worker.
- `new_context(scenario_name, video_dir=None) -> BrowserContext` — fresh isolated context per scenario; viewport, locale, timezone, video, and trace toggled from config.
- `new_page(ctx) -> Page` — fresh page for the context.
- `stop_trace(ctx, trace_path)` — finalise the Playwright trace zip.

#### `logger.py`
**Purpose:** dual logging — `loguru` for ergonomics, stdlib `logging` for library compatibility.
**Class:** `InterceptHandler` — routes stdlib records into loguru.
**Functions:**
- `configure_logging(level)` — idempotent; wires stdout sink (coloured), file sink (`logs/qaforge.log`, 10 MB rotation, 14-day retention, zip compression).
- `get_logger(name)` — returns a bound loguru logger.
**Security:** `diagnose=False` on the file sink prevents secret values from showing up in tracebacks.

#### `retry.py`
**Purpose:** thin tenacity wrapper for retry semantics on flaky operations (network, eventual consistency).
**Function:** `retry_on(exceptions, attempts, min_wait, max_wait)` — exponential backoff decorator. Used sparingly; prefer Playwright auto-waits and explicit `expect()` over retry.

### 3.4  Pages (`src/qaforge/pages/`)

#### `base_page.py`
**Purpose:** shared building block. `URL_PATH` per page; `open()` joins it to `base_url`. Helpers: `screenshot`, `expect_visible`, `expect_text`, `expect_url`. Uses Playwright's `expect` (auto-retrying) — never `time.sleep`.

#### `login_page.py`
**Locators:** `email_input`, `password_input`, `otp_input`, `submit_btn`, `error_banner`. All role/label-based — resilient to DOM churn.
**Methods:**
- `login(email, password, otp=None)` — fills credentials and submits, capturing the `/auth/login` response and asserting it succeeded.
- `expect_login_failed(message)` — visible error banner contains `message`.

#### `dashboard_page.py`
**Locators:** `welcome_header`, `user_menu`, `nav_settings`.
**Methods:** `open_settings()`, `expect_logged_in_as(email)`.

#### `form_page.py`
Demonstrates the broadest Playwright surface area: text fields, dropdown (`select_option`), checkbox, file upload (`set_input_files`), iframe captcha (`frame_locator`), and download interception (`expect_download`).

### 3.5  API layer (`src/qaforge/api/`)

#### `auth_manager.py`
**Purpose:** single source of auth tokens for every protocol.
**Class:** `AuthManager(cfg)`.
**Methods:**
- `oauth_token(scope=None) -> AuthToken` — client_credentials grant. Cached by scope.
- `password_otp_token(email, password, otp) -> AuthToken` — two-step user login + 2FA. Cached by email.
- `assume_role(role) -> AuthToken` — convenience wrapper that maps a role name (`admin`/`editor`/`viewer`) to an OAuth scope. Powers RBAC scenarios.
**Type:** `AuthToken` — `access_token`, `token_type`, `expires_at`; `is_valid()` rejects tokens within 30s of expiry; `header` returns the `Authorization` dict.

#### `contract_validator.py`
**Purpose:** JSON-schema response validation backed by Draft 2020-12.
**Function:** `validate_against_contract(payload, contract_name)` — loads `test_data/static/contracts/<name>.json`, raises `ValidationError` listing every mismatch with JSON pointers.

#### `rest/client.py` — `RestClient`
**Purpose:** wraps `httpx.Client`. Methods: `get/post/put/patch/delete/head`.
**Auth fluent helpers:** `with_oauth(scope)`, `with_password_otp(email, password, otp)`, `with_role(role)`, `clear_auth()` — all return `self` for chaining.
**Logging:** every request emits `<METHOD> <path> -> <status> in <ms>` at DEBUG.
**Note:** 4xx/5xx are **not** auto-raised so negative scenarios can assert the failure status explicitly.

#### `rest/endpoints/users.py` — `UsersAPI`
Domain wrapper: `list_users`, `get_user`, `create_user`, `update_user`, `delete_user`. Add a sibling file (e.g. `orders.py`) for each endpoint group.

#### `graphql/client.py` — `GraphQLClient`
**Purpose:** sync GraphQL via the `gql` library.
**Methods:** `query(document, variables)`, `mutation(document, variables)`, `introspect()`. Operations live in `graphql/operations.py` — never inline them in steps.

#### `graphql/operations.py`
Constants for `GET_USER_QUERY`, `LIST_USERS_QUERY`, `CREATE_USER_MUTATION`, `DELETE_USER_MUTATION`. Single source of truth for GraphQL strings.

#### `grpc/client.py` — `GrpcClient`
**Purpose:** thin façade for unary, server-streaming, client-streaming, bidi RPCs.
**Methods:** `connect()`, `with_oauth(scope)`, `auth_metadata()`, `stub(stub_class)`, `collect_server_stream(call)`, `close()`.
**Stub generation:** see `scripts/gen_grpc.sh`.

#### `websocket/client.py` — `WebSocketClient`
**Purpose:** sync façade over `websockets` (asyncio under the hood).
**Methods:** `with_oauth(scope)`, `send_and_receive(message, expect_messages, timeout_seconds)`, `stream(send_message, duration_seconds)`, `close()`.

#### `async_api/kafka_client.py`
**Classes:** `KafkaTestProducer` (`start/send/stop`), `KafkaTestConsumer` (`start/poll/stop`). Sync wrappers around `aiokafka` so steps stay readable. JSON ser/deser is the default.

### 3.6  Database layer (`src/qaforge/database/`)

All four engines expose the same conceptual API:

| Concern        | Postgres / MySQL                                | Mongo                                            | Dynamo                                            |
| -------------- | ----------------------------------------------- | ------------------------------------------------ | ------------------------------------------------- |
| Connect        | `connect()` returns `self`                      | `connect()` returns `self`                       | constructor; no separate connect (boto3 idiom)    |
| Read           | `query`, `query_one`                            | `find`, `count`                                  | `get_item`, `query`, `scan_filter`                |
| Write          | `execute`, `executemany`                        | `insert_one`                                     | `put_item`                                        |
| Transaction    | `with txn(): ...` (rolls back)                  | n/a                                              | n/a                                               |
| Assert         | `assert_row_count(table, where, params, n)`     | `assert_doc_exists(col, filt)`                   | `assert_item_exists(table, key)`                  |
| Cleanup        | `cleanup_test_rows(table, where, params)`       | `cleanup(col, filt)`                             | `cleanup(table, keys)`                            |

**Common rule:** never string-format SQL — always pass parameters separately. The Postgres and MySQL clients use `%s` placeholders (psycopg & PyMySQL convention).

### 3.7  AI layer (`src/qaforge/ai/`)

#### `deepeval_runner/runner.py` — `DeepEvalRunner`
**Metrics:** `answer_relevancy`, `faithfulness`, `hallucination`, `bias`, `toxicity`, `custom_geval`.
Each returns a `MetricResult` (`name`, `passed`, `score`, `reason`, `threshold`). Thresholds default to values in `cfg.ai.thresholds` and can be overridden per call.

#### `ragas_runner/runner.py` — `RagasRunner`
**Metrics:** `faithfulness`, `answer_relevancy`, `context_precision`, `context_recall`.
**Methods:** `evaluate_single(question, answer, contexts, ground_truth)`, `evaluate_batch(...)`. Returns `RagasResult` with per-metric scores and an aggregate `passed` flag.

### 3.8  Test data (`src/qaforge/data/`)

#### `faker_factory.py`
- `unique_email(domain)` — uniqueness via UUID4 hex prefix.
- `user_payload(role)` — full user dict with address sub-doc.
- `order_payload(user_id, items)` — composite payload for order tests.
- `bulk_users(n, role)` — list of N users.
- Deterministic seeding via `QAFORGE_FAKER_SEED`.

#### `loaders.py`
- `load_json(rel)`, `load_yaml(rel)` — cached.
- `load_csv(rel)` — list-of-dicts via `DictReader`.
- `static_user(key)` — typed fetch of a known user from `test_data/static/users.json`.

#### `db_seeder.py`
**Class:** `DBSeeder(cfg)`.
**Methods:** `seed_postgres`, `seed_mysql`, `seed_mongo`, `seed_dynamo`, `seed_all`. Idempotent — uses `ON CONFLICT DO NOTHING` / `INSERT IGNORE` / `update_one(..., upsert=True)` / `put_item`.

### 3.9  Reporting (`src/qaforge/reporting/`)

#### `allure_helpers.py`
**Functions:** `attach_screenshot`, `attach_video`, `attach_trace`, `attach_json`, `attach_text`. The Allure formatter itself is wired in `behave.ini`.

#### `extent_reporter.py`
Thread-safe singleton accumulator. Step authors don't touch it; `environment.py` writes scenario records. `finalize()` dumps to `reports/extent/extent.json`.

#### `custom_dashboard.py`
**Function:** `render_dashboard()` — Jinja2 template renders `extent.json` to a single static `dashboard.html`. No JS, no server, no external CSS — copy/paste-able into Slack or email.

### 3.10  Hooks (`src/qaforge/hooks/`)

#### `cleanup.py` — `CleanupRegistry`
LIFO stack of cleanup callables registered by steps via `context.cleanup.add(fn)`. `run_all()` runs them in `after_scenario` and swallows individual failures (so one bad cleanup doesn't mask another).

### 3.11  Utilities (`src/qaforge/utils/`)

#### `network.py`
- `NetworkRecorder(page)` — captures every Playwright `request` event for later assertions.
- `stub_route(page, url_glob, status, json_body=None, body=None)` — fulfil mock responses.
- `block_third_party(page, allowed_hosts)` — abort any request not matching the allowlist (excellent for ad/tracker isolation).

### 3.12  Features and steps (`features/`)

#### `environment.py`
See §2 above for the lifecycle table.

#### `steps/common_steps.py`
Cross-cutting: `I am running against the "<env>" environment`, `a known user "<key>"`, `a freshly generated user with role "<role>"`, `I have an OAuth token for role "<role>"`, `the response status should be <n>`.

#### `steps/ui_steps.py`
Page navigation, login, form submission, downloads, captcha iframe, network recording, network stubbing.

#### `steps/rest_steps.py`
REST authentication, list/get/create/patch users, contract validation, body field assertions.

#### `steps/graphql_steps.py`
Schema introspection, queries, mutations, response field assertions.

#### `steps/grpc_steps.py`
Unary `GetUser`, server-streaming `ListUsers`. Imports generated stubs lazily.

#### `steps/ws_steps.py`
Send-and-receive, streaming subscriptions, reply assertions.

#### `steps/db_steps.py`
Postgres / MySQL row-count assertions, Mongo doc-exists, Dynamo item-exists, Postgres cleanup registration.

#### `steps/ai_steps.py`
DeepEval (relevancy, faithfulness, hallucination, bias+toxicity, custom GEval) and RAGAs assertions.

### 3.13  Test data (`test_data/`)

| Path                                  | Purpose                                                               |
| ------------------------------------- | --------------------------------------------------------------------- |
| `static/users.json`                   | Known users referenced by the `static_user(key)` loader.              |
| `static/contracts/*.json`             | JSON-schema response contracts (Draft 2020-12).                       |
| `static/seed_<engine>.json`           | DB seed fixtures consumed by `DBSeeder`.                              |
| `static/rag_corpus.json`              | Reference corpus used in RAG quality scenarios.                       |
| `static/sample.pdf`                   | Placeholder upload artefact for form tests.                           |
| `csv/*.csv` / `json/*.json`           | External datasets for parameterised scenarios.                        |

### 3.14  Docker (`docker/`)

#### `Dockerfile`
Built on `mcr.microsoft.com/playwright/python:v1.48.0-jammy` so all browser dependencies are pre-installed. Layered cache: deps install before source copy.

#### `docker-compose.yml`
Sandbox stack: Postgres 16, MySQL 8, Mongo 7, DynamoDB-local, plus the QAForge runner. Wait-for-healthy ordering on relational DBs.

### 3.15  CI (`.github/workflows/ci.yml`)

Single `smoke` job: checkout → set up Python → install deps + chromium → run `scripts/run.sh smoke dev` → upload `reports/` as an artefact. Extend with regression / staging matrix as needed.

---

## 4. Adding a new test type — recipe

> Goal: add a contract test that hits a new `/billing` REST endpoint and validates a JSON-schema contract.

1. **Schema** — drop `test_data/static/contracts/billing.invoice.v1.json`.
2. **Endpoint wrapper** — create `src/qaforge/api/rest/endpoints/billing.py` with `BillingAPI`.
3. **Step file** — extend `features/steps/rest_steps.py` (or add `billing_steps.py`):
   ```python
   @when('I fetch invoice "{invoice_id}"')
   def step(context, invoice_id):
       context.response = BillingAPI(context.rest).get_invoice(invoice_id)
       context.response_status = context.response.status_code
   ```
4. **Feature** — add `features/api/rest/billing.feature` with `@api @rest` tags.
5. Run `bash scripts/run.sh rest dev`.

That's the whole loop. No framework changes were necessary — the layered design absorbs new endpoints into the existing scaffolding.

---

## 5. Operating in production safely

QAForge supports running smoke against real prod, with two safeguards layered:

1. **`@no_prod` tag** — every destructive scenario must carry it. `before_scenario` skips them when `cfg.read_only` is true (prod YAML).
2. **Read-only DB users** — `prod.yaml` points DB connections at read-only replicas (`prod-pg-readonly.example.com`, `prod-mysql-ro.example.com`). The DB clients have no privilege to write even if a careless step tried.

Always invoke prod runs with `behave -t @smoke -t ~@no_prod -D env=prod` so the tag exclusion is explicit at the command line as well.
