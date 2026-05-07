# QAForge

> **Production-grade BDD automation framework for AI-powered SaaS**
> Behave · Playwright · REST · GraphQL · gRPC · WebSocket · Async (Kafka) · PostgreSQL · MySQL · MongoDB · DynamoDB · DeepEval · RAGAs

QAForge is the test automation framework you would build on day one at a MAANG-level org if your stack were Next.js + FastAPI + an LLM service: typed config, isolated protocol clients, real reports, parallelism, and Docker out of the box.

---

## 1. Why QAForge

| Concern              | How QAForge solves it                                                                     |
| -------------------- | ----------------------------------------------------------------------------------------- |
| BDD ergonomics       | Pure **Behave** (no pytest), Gherkin first, parallel via **Behavex**                      |
| UI flakiness         | **Playwright** auto-waits, traces on failure, video, screenshots, retries                 |
| API breadth          | One isolated subpackage per protocol; remove one, others keep working                     |
| AI quality gates     | **DeepEval** for LLM metrics (relevancy, faithfulness, hallucination, bias, toxicity, GEval), **RAGAs** for RAG pipelines |
| Multi-DB validation  | First-class clients for **Postgres, MySQL, Mongo, DynamoDB**                              |
| Reporting            | **Allure** + **Extent-style JSON** + **single-file HTML dashboard**                       |
| Reproducibility      | **Docker** image + **docker-compose** sandbox with all DBs                                 |
| Safety in prod       | `@no_prod` tag + `read_only: true` config — destructive scenarios skipped                 |

---

## 2. Folder structure

```
qaforge/
├── behave.ini                       # Behave config (formatters, userdata)
├── pyproject.toml                   # Build metadata
├── requirements.txt                 # Pinned deps
├── .env.example                     # Secrets template
│
├── config/                          # Environment configs
│   ├── environments/
│   │   ├── dev.yaml
│   │   ├── staging.yaml
│   │   └── prod.yaml
│   └── tags.json                    # Suite/tag metadata
│
├── proto/                           # gRPC .proto definitions
│   └── user_service.proto
│
├── src/qaforge/                     # Framework source (importable as `qaforge`)
│   ├── core/
│   │   ├── config_loader.py         # Pydantic-typed YAML loader
│   │   ├── browser_factory.py       # Playwright lifecycle
│   │   ├── logger.py                # Loguru ↔ stdlib bridge
│   │   └── retry.py                 # Tenacity-based decorator
│   ├── pages/                       # POM
│   │   ├── base_page.py
│   │   ├── login_page.py
│   │   ├── dashboard_page.py
│   │   └── form_page.py
│   ├── api/
│   │   ├── auth_manager.py          # OAuth + Password+OTP + RBAC tokens
│   │   ├── contract_validator.py    # JSON-schema response validation
│   │   ├── rest/                    # REST client + endpoint wrappers
│   │   ├── graphql/                 # GraphQL client + operation library
│   │   ├── grpc/                    # gRPC client + generated stubs
│   │   ├── websocket/               # Sync facade over websockets
│   │   └── async_api/               # Kafka producer/consumer
│   ├── database/
│   │   ├── postgres/
│   │   ├── mysql/
│   │   ├── mongo/
│   │   └── dynamo/
│   ├── ai/
│   │   ├── deepeval_runner/         # LLM metrics
│   │   └── ragas_runner/            # RAG metrics
│   ├── data/
│   │   ├── faker_factory.py         # Dynamic data
│   │   ├── loaders.py               # CSV, JSON, YAML loaders
│   │   └── db_seeder.py             # DB seeding
│   ├── reporting/
│   │   ├── allure_helpers.py
│   │   ├── extent_reporter.py
│   │   └── custom_dashboard.py      # Jinja2 HTML dashboard
│   ├── hooks/
│   │   └── cleanup.py               # Per-scenario cleanup registry
│   └── utils/
│       └── network.py               # Playwright network interception
│
├── features/                        # Behave tests
│   ├── environment.py               # Lifecycle hooks
│   ├── steps/
│   │   ├── common_steps.py
│   │   ├── ui_steps.py
│   │   ├── rest_steps.py
│   │   ├── graphql_steps.py
│   │   ├── grpc_steps.py
│   │   ├── ws_steps.py
│   │   ├── db_steps.py
│   │   └── ai_steps.py
│   ├── ui/                          # *.feature files
│   ├── api/{rest,graphql,grpc,websocket}/
│   ├── database/
│   └── ai/
│
├── test_data/
│   ├── static/
│   │   ├── users.json
│   │   ├── contracts/*.json         # JSON-schema contracts
│   │   ├── seed_*.json              # DB seed fixtures
│   │   └── rag_corpus.json
│   ├── csv/
│   └── json/
│
├── reports/                         # Generated artefacts (gitignored)
│   ├── allure/
│   ├── extent/extent.json
│   ├── custom/dashboard.html
│   ├── screenshots/
│   ├── videos/
│   ├── traces/
│   └── junit/
│
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── scripts/
│   ├── run.sh                       # Suite runner
│   └── gen_grpc.sh                  # Regenerate gRPC stubs
│
├── docs/
│   ├── manuals/
│   │   └── framework_manual.md      # File-by-file reference
│   └── technology_guides/           # 15 deep-dive guides
│
└── .github/workflows/ci.yml
```

### Folder roles in one line each

- **config/** — environment-specific YAML; switch with `-D env=staging`.
- **src/qaforge/core/** — config, logging, browser, retry. Touch carefully; everything depends on it.
- **src/qaforge/pages/** — POM. One class per logical page or component.
- **src/qaforge/api/{rest,graphql,grpc,websocket,async_api}/** — fully isolated protocol clients. Drop a folder, the others still work.
- **src/qaforge/database/{postgres,mysql,mongo,dynamo}/** — isolated DB clients with the same shape (`connect`, `query`, `execute`, `cleanup`).
- **src/qaforge/ai/** — DeepEval + RAGAs wrappers.
- **src/qaforge/data/** — static, dynamic (Faker), and DB-seed data providers.
- **src/qaforge/reporting/** — Allure helpers + Extent JSON + HTML dashboard renderer.
- **src/qaforge/hooks/** — per-scenario cleanup registry used by `environment.py`.
- **features/** — Gherkin features and step definitions.
- **test_data/** — fixtures: users, contracts, CSVs, RAG corpus.
- **reports/** — all generated artefacts.
- **docker/** — image + sandbox compose stack.
- **docs/** — framework manual + per-technology guides.

---

## 3. Setup

### Prerequisites

- Python ≥ 3.11
- Node.js (only if you want to run `allure` CLI locally)
- Docker (optional, for sandbox stack)

### Local install

```bash
git clone <your-repo> qaforge && cd qaforge
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install --with-deps        # downloads chromium/firefox/webkit
cp .env.example .env                  # then edit values
```

If you'll touch gRPC tests:

```bash
bash scripts/gen_grpc.sh              # regenerates stubs from proto/*.proto
```

---

## 4. Running tests

The wrapper `scripts/run.sh <suite> <env> <browser> <workers>` is the easy path.

```bash
# Smoke on dev
bash scripts/run.sh smoke dev

# Full regression on staging in firefox, 8 workers
bash scripts/run.sh regression staging firefox 8

# Just AI tests on dev
bash scripts/run.sh ai dev
```

### Direct Behave

```bash
# By tag
behave -t @smoke -D env=dev -D browser=chromium -D headless=true

# Specific feature
behave features/ui/login.feature -D env=dev

# Multiple tags (AND): smoke and not no_prod
behave -t @smoke -t ~@no_prod -D env=prod
```

### Parallel execution (Behavex)

Behavex shards scenarios across processes. Each worker gets its own browser
and clients, so tests must remain stateless across scenarios (which they are
by design here).

```bash
behavex --parallel-processes 8 --parallel-scheme scenario \
  -t @regression -D env=staging -D browser=chromium
```

`--parallel-scheme feature` is also supported when scenarios within a feature
share heavy fixtures.

---

## 5. Reporting

After every run you get **three** report artefacts:

| Artefact                     | Path                            | Generated by                      |
| ---------------------------- | ------------------------------- | --------------------------------- |
| Allure HTML                  | `reports/allure/report/`        | `allure_behave.formatter`          |
| Extent-style JSON            | `reports/extent/extent.json`    | `qaforge.reporting.extent_reporter` |
| Single-file HTML dashboard   | `reports/custom/dashboard.html` | `qaforge.reporting.custom_dashboard` |

Open the dashboard:

```bash
xdg-open reports/custom/dashboard.html       # Linux
open    reports/custom/dashboard.html         # macOS
```

Open Allure:

```bash
allure serve reports/allure/results
```

Failed UI scenarios automatically attach: full-page **screenshot**, **video**,
and **Playwright trace** to the Allure report.

---

## 6. Docker

### Just the runner

```bash
docker build -f docker/Dockerfile -t qaforge:latest .
docker run --rm -v $PWD/reports:/app/reports qaforge:latest \
  bash scripts/run.sh smoke dev
```

### Full sandbox (Postgres + MySQL + Mongo + DynamoDB-local + runner)

```bash
docker compose -f docker/docker-compose.yml up --abort-on-container-exit
```

---

## 7. Customising the framework

### Add a new page object

```python
# src/qaforge/pages/billing_page.py
from qaforge.pages.base_page import BasePage

class BillingPage(BasePage):
    URL_PATH = "/billing"
    @property
    def add_card_btn(self): return self.page.get_by_role("button", name="Add card")
    def open_add_card(self): self.add_card_btn.click()
```

Use it in a step:

```python
from qaforge.pages.billing_page import BillingPage

@when('I open the add-card form')
def step(context):
    BillingPage(context.page, context.cfg.ui.base_url).open_add_card()
```

### Add a new REST endpoint group

```python
# src/qaforge/api/rest/endpoints/orders.py
class OrdersAPI:
    BASE = "/orders"
    def __init__(self, client): self.client = client
    def list(self, **q): return self.client.get(self.BASE, params=q)
    def create(self, payload): return self.client.post(self.BASE, json=payload)
```

### Add a new environment

Drop `config/environments/uat.yaml`, mirroring `dev.yaml`. Run with `-D env=uat`.

### Add a new test-data source

CSV fixtures: drop into `test_data/csv/<name>.csv`, then:

```python
from qaforge.data.loaders import load_csv
rows = load_csv("csv/users_bulk.csv")
```

### Customise logging

Edit `qaforge.core.logger.configure_logging` — sinks, format, rotation, retention. Loguru intercepts stdlib too, so library logs (Playwright, requests, boto3) flow through the same sinks.

### Customise reporting

- Add metadata to scenarios: `allure.dynamic.label("owner", "team-payments")` inside a step.
- Extend the dashboard: edit `_TEMPLATE` in `custom_dashboard.py`.

---

## 8. Tag glossary

| Tag           | Meaning                                                          |
| ------------- | ---------------------------------------------------------------- |
| `@smoke`      | Critical-path scenarios run on every commit                      |
| `@regression` | Full regression sweep                                            |
| `@ui`         | Drives Playwright (browser is provisioned)                       |
| `@api`        | Generic API; usually combined with one of the protocol tags      |
| `@rest`       | REST scenarios (`RestClient` is provisioned)                     |
| `@graphql`    | GraphQL (`GraphQLClient` is provisioned)                         |
| `@grpc`       | gRPC (`GrpcClient` is provisioned and connected)                 |
| `@websocket`  | WebSocket (`WebSocketClient` is provisioned)                     |
| `@kafka`      | Kafka producer is provisioned                                    |
| `@db`         | Generic DB tag (Postgres client provisioned by default)          |
| `@postgres` / `@mysql` / `@mongo` / `@dynamo` | Engine-specific DB scenario     |
| `@ai`         | DeepEval + RAGAs evaluators are provisioned                      |
| `@no_prod`    | Skipped automatically when `read_only: true` (prod environment)  |

---

## 9. Where to read next

- **`docs/manuals/framework_manual.md`** — file-by-file reference.
- **`docs/technology_guides/`** — 15 deep-dive guides (Playwright commands, REST/GraphQL/gRPC/WS/Kafka, the four DB engines, YAML, Docker, Faker, Logging).

---

## 10. License

MIT.
