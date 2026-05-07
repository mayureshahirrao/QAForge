#!/usr/bin/env bash
# scripts/run.sh — convenience wrapper around behave / behavex.
#
# Examples:
#   scripts/run.sh smoke dev                   # smoke suite on dev (parallel)
#   scripts/run.sh regression staging chromium # regression on staging in chromium
#   scripts/run.sh ai dev                      # AI suite (DeepEval + RAGAs)
set -euo pipefail

SUITE="${1:-smoke}"
ENV="${2:-dev}"
BROWSER="${3:-chromium}"
WORKERS="${4:-4}"

case "$SUITE" in
  smoke)      TAGS="@smoke" ;;
  regression) TAGS="@regression" ;;
  ui)         TAGS="@ui" ;;
  api)        TAGS="@api" ;;
  rest)       TAGS="@rest" ;;
  graphql)    TAGS="@graphql" ;;
  grpc)       TAGS="@grpc" ;;
  websocket)  TAGS="@websocket" ;;
  db)         TAGS="@db" ;;
  ai)         TAGS="@ai" ;;
  all)        TAGS="" ;;
  *) echo "Unknown suite: $SUITE"; exit 1 ;;
esac

mkdir -p reports/allure/results reports/junit reports/extent reports/custom

# Parallel via behavex (recommended)
echo ">>> Running $SUITE on $ENV ($BROWSER, $WORKERS workers)"
if [ -n "$TAGS" ]; then
  behavex --parallel-processes "$WORKERS" --parallel-scheme scenario \
    -t "$TAGS" \
    -D env="$ENV" -D browser="$BROWSER" -D headless=true \
    -f allure_behave.formatter:AllureFormatter -o reports/allure/results
else
  behavex --parallel-processes "$WORKERS" --parallel-scheme scenario \
    -D env="$ENV" -D browser="$BROWSER" -D headless=true \
    -f allure_behave.formatter:AllureFormatter -o reports/allure/results
fi

echo ">>> Generating Allure report"
allure generate reports/allure/results -o reports/allure/report --clean || true
echo ">>> Done. Open: reports/custom/dashboard.html  reports/allure/report/index.html"
