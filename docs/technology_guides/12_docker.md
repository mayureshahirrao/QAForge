# 12 — Docker

> **Source files:** `docker/Dockerfile`, `docker/docker-compose.yml`, `scripts/run.sh`, `.github/workflows/ci.yml`.

---

## 1. Why Docker for tests

- **Reproducibility.** Same Python, same browsers, same OS libs — every dev, every CI run.
- **Isolation.** Spin up Postgres + MySQL + Mongo + Dynamo locally with one command; tear down with another.
- **CI parity.** What works locally in `docker compose up` is what runs in GitHub Actions.

---

## 2. The Dockerfile

```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONPATH=/app/src QAFORGE_ENV=dev QAFORGE_LOG_LEVEL=INFO
RUN playwright install --with-deps chromium firefox webkit
CMD ["bash", "scripts/run.sh", "smoke", "dev", "chromium", "4"]
```

Key choices:

- **Base image:** `mcr.microsoft.com/playwright/python` already has the OS libs Playwright browsers need (`libnss3`, `libgbm1`, fonts, …). Avoids the "works on my laptop" trap.
- **Layer order:** `requirements.txt` is copied **before** the rest of the source. Pip layer is cached as long as deps don't change; source edits don't bust the cache.
- **`PYTHONPATH=/app/src`** so `import qaforge.…` works without installing the package.
- **Browsers installed at build time** to avoid network access at run time (some CI sandboxes block it).

Build and run:

```bash
docker build -f docker/Dockerfile -t qaforge:latest .
docker run --rm \
  -v $PWD/reports:/app/reports \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  qaforge:latest \
  bash scripts/run.sh smoke dev
```

---

## 3. docker-compose — the full sandbox

```yaml
services:
  postgres: { image: postgres:16-alpine, healthcheck: ... }
  mysql:    { image: mysql:8,            healthcheck: ... }
  mongo:    { image: mongo:7 }
  dynamo:   { image: amazon/dynamodb-local:latest }
  qaforge:
    build: { context: .., dockerfile: docker/Dockerfile }
    depends_on:
      postgres: { condition: service_healthy }
      mysql:    { condition: service_healthy }
      mongo:    { condition: service_started }
      dynamo:   { condition: service_started }
    environment:
      QAFORGE_ENV: dev
      PG_USER: qa
      PG_PASSWORD: qa
      MYSQL_USER: qa
      MYSQL_PASSWORD: qa
      MONGO_URI: "mongodb://mongo:27017"
      AWS_ACCESS_KEY_ID: dummy
      AWS_SECRET_ACCESS_KEY: dummy
      AWS_DEFAULT_REGION: us-east-1
    volumes:
      - ../reports:/app/reports
      - ../logs:/app/logs
```

Run:

```bash
# All services + smoke
docker compose -f docker/docker-compose.yml up --abort-on-container-exit

# Run regression interactively
docker compose -f docker/docker-compose.yml run --rm qaforge \
  bash scripts/run.sh regression dev firefox 8
```

The `condition: service_healthy` clauses ensure Postgres/MySQL accept connections before the runner starts — without them, you'd get sporadic `connection refused` flakes.

---

## 4. Reports as bind mounts

The `volumes` section binds `../reports` and `../logs` to the runner. After the container exits, your local checkout has every screenshot, video, trace, log, and report — Allure, Extent JSON, and the HTML dashboard.

---

## 5. CI integration

`.github/workflows/ci.yml` deliberately uses **direct setup** (not Docker) for speed — caching pip is faster than building images. Production teams typically have a separate workflow that builds and pushes the image (use it as a base for nightly suites).

---

## 6. Headless inside Docker

The Dockerfile sets `headless=true` by default. To debug interactively:

```bash
docker run --rm -it \
  -e QAFORGE_HEADLESS=false \
  -p 5900:5900 \
  qaforge:latest \
  bash
```

…then run a single feature with `behave -D headless=false`. (For VNC, you'd add `x11vnc` to the image — out of scope for the default build.)

---

## 7. Best practices

- **Don't mount the source tree** in the runner image when you want to test what you built. Mount only `reports/` and `logs/` (writable).
- **Keep the image lean.** Pin `requirements.txt`. Don't `apt-get install` ad hoc tools.
- **Use one image per role.** Test runner image is for tests; don't reuse it for application builds.
- **Network: same compose network.** All services in one compose file are on the same default bridge — host names match service names (`postgres`, `mysql`, …).
