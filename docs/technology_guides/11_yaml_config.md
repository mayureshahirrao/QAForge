# 11 — YAML Configuration

> **Source files:** `config/environments/*.yaml`, `src/qaforge/core/config_loader.py`, `config/tags.json`.

---

## 1. Why YAML (and why typed)

YAML is the lingua franca of config in Python. QAForge layers two safety nets on top:

1. **Pydantic validation.** The `Config` model in `config_loader.py` validates every field at startup. A typo (`base_uri`) fails fast, not after 30 minutes.
2. **Env-var indirection for secrets.** YAML files contain only the *names* of secret env vars (e.g. `password_env: PG_PASSWORD`). The actual value is resolved at runtime via `secret(env_name)`.

This gives you reviewable, version-controlled config without ever committing a credential.

---

## 2. Structure

```yaml
environment: dev                         # name (must match filename)

ui:
  base_url: "https://dev.app.example.com"
  default_timeout_ms: 30000
  navigation_timeout_ms: 45000
  viewport: { width: 1920, height: 1080 }
  locale: "en-US"
  timezone: "UTC"
  record_video: true
  trace: "retain-on-failure"
  screenshot_on_failure: true
  slow_mo_ms: 0

api:
  rest:    { base_url: "...", timeout_seconds: 30 }
  graphql: { endpoint: "..." }
  grpc:    { host: "...", port: 50051, use_tls: true }
  websocket: { url: "wss://..." }
  async_api: { kafka_brokers: ["...:9092"] }

auth:
  oauth:
    token_url: "..."
    client_id_env: OAUTH_CLIENT_ID
    client_secret_env: OAUTH_CLIENT_SECRET
    scope: "read write"
  password_otp:
    login_url: "..."
    otp_url:   "..."

databases:
  postgres: { host: "...", port: 5432, db: "appdb",
              user_env: PG_USER, password_env: PG_PASSWORD }
  mysql:    { ... }
  mongo:    { uri_env: MONGO_URI, db: "appdb" }
  dynamo:   { region: "us-east-1", endpoint: null }

ai:
  llm_provider: openai
  llm_model: gpt-4o-mini
  api_key_env: OPENAI_API_KEY
  rag_corpus_path: "test_data/static/rag_corpus.json"
  thresholds:
    answer_relevancy: 0.75
    faithfulness: 0.80
    context_precision: 0.70

read_only: false                         # prod sets this true → @no_prod scenarios skipped
```

---

## 3. Switching environments

Three precedences (highest first):

1. `behave -D env=staging`
2. `QAFORGE_ENV=staging behave ...`
3. Default `dev`

`scripts/run.sh smoke staging` does this for you.

---

## 4. Adding a new environment

Drop `config/environments/uat.yaml` mirroring `dev.yaml`, then run with `-D env=uat`. Pydantic will validate it on first load — any missing or malformed field fails immediately with a precise error.

---

## 5. Secrets — the discipline

- **Never** put a literal secret in YAML.
- **Always** reference an env var via the `*_env` field.
- The `secret(env_var)` helper raises `EnvironmentError` if a referenced var is unset, so misconfiguration is loud.
- In CI, set secrets via the platform's secret manager (GitHub Actions `secrets`, GitLab `CI/CD variables`, Vault, etc.).

---

## 6. Tags — `config/tags.json`

The companion JSON config maps suite names to tag expressions and parallel worker counts:

```json
{
  "suites": {
    "smoke":      { "tags": ["@smoke"],       "parallel_workers": 4 },
    "regression": { "tags": ["@regression"],  "parallel_workers": 8 }
  }
}
```

`scripts/run.sh` reads this when figuring out what tags to pass to behavex.

---

## 7. Validation in practice

```python
from qaforge.core.config_loader import load_config
cfg = load_config({"env": "dev"})
print(cfg.ui.base_url)              # IDE/typing-friendly
print(cfg.databases.postgres.port)  # int, not str
```

If `dev.yaml` had `port: "five-thousand"`, Pydantic would raise on `load_config(...)`:

```
ValidationError: 1 validation error for Config
databases.postgres.port
  Input should be a valid integer (type=type_error.integer)
```

---

## 8. Best practices

- **Keep the YAML alphabetised within each section.** Easier diffs.
- **One value per environment.** Don't reach for `${ENV_VAR}` interpolation inside YAML — that's what `*_env` indirection is for.
- **Don't commit `prod.yaml` overrides** that point to dev hostnames. Periodic linting checks (`grep dev. prod.yaml`) catch this.
- **Add a Pydantic field, not a stringly-typed lookup.** When you add a config key, declare it in the `Config` model so validation enforces it everywhere.
