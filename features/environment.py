"""
features/environment.py
=======================
Behave lifecycle hooks. This file is auto-discovered by Behave.

Lifecycle:
  before_all          -> load config, configure logging, init reporters
  before_feature      -> create per-feature output dirs
  before_scenario     -> open browser context, init API/DB clients, register cleanup
  before_step         -> capture step start time
  after_step          -> capture step status & duration; attach screenshot on UI failure
  after_scenario      -> stop trace, save video, run cleanup, append Extent record
  after_feature       -> nothing (kept for symmetry)
  after_all           -> finalize Extent JSON, render custom dashboard
"""
from __future__ import annotations

import os
import sys
import time
import traceback
from pathlib import Path

# Make src/ importable when running `behave` from repo root
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qaforge.api.async_api.kafka_client import KafkaTestConsumer, KafkaTestProducer  # noqa: E402
from qaforge.api.auth_manager import AuthManager  # noqa: E402
from qaforge.api.graphql.client import GraphQLClient  # noqa: E402
from qaforge.api.grpc.client import GrpcClient  # noqa: E402
from qaforge.api.rest.client import RestClient  # noqa: E402
from qaforge.api.websocket.client import WebSocketClient  # noqa: E402
from qaforge.core.browser_factory import BrowserFactory  # noqa: E402
from qaforge.core.config_loader import load_config  # noqa: E402
from qaforge.core.logger import configure_logging, get_logger  # noqa: E402
from qaforge.database.dynamo.client import DynamoTestClient  # noqa: E402
from qaforge.database.mongo.client import MongoTestClient  # noqa: E402
from qaforge.database.mysql.client import MySQLClient  # noqa: E402
from qaforge.database.postgres.client import PostgresClient  # noqa: E402
from qaforge.hooks.cleanup import CleanupRegistry  # noqa: E402
from qaforge.reporting.allure_helpers import attach_screenshot, attach_trace, attach_video  # noqa: E402
from qaforge.reporting.custom_dashboard import render_dashboard  # noqa: E402
from qaforge.reporting.extent_reporter import ExtentReporter, ScenarioReport, StepReport  # noqa: E402

REPORTS = ROOT / "reports"
SCREENSHOTS = REPORTS / "screenshots"
VIDEOS = REPORTS / "videos"
TRACES = REPORTS / "traces"
for d in (SCREENSHOTS, VIDEOS, TRACES):
    d.mkdir(parents=True, exist_ok=True)

log = get_logger("environment")


# --------------------------- before_all ---------------------------
def before_all(context):
    configure_logging(level=os.environ.get("QAFORGE_LOG_LEVEL", "INFO"))
    context.cfg = load_config(context.config.userdata)
    context.browser_name = context.config.userdata.get("browser", "chromium")
    context.headless = context.config.userdata.getbool("headless", True)
    context.retry_failed = int(context.config.userdata.get("retry_failed", 1))
    context.reporter = ExtentReporter(environment=context.cfg.environment)

    # Browser is started once per worker (process), reused across scenarios
    context.browser_factory = BrowserFactory(context.cfg, context.browser_name, context.headless)
    context.browser_factory.start()
    log.info(
        f"QAForge starting | env={context.cfg.environment} browser={context.browser_name} "
        f"headless={context.headless}"
    )


# --------------------------- before_feature ---------------------------
def before_feature(context, feature):
    feature.feature_dir = REPORTS / "features" / feature.name.replace(" ", "_")
    feature.feature_dir.mkdir(parents=True, exist_ok=True)


# --------------------------- before_scenario ---------------------------
def before_scenario(context, scenario):
    # Skip destructive scenarios in prod
    if context.cfg.read_only and "no_prod" in scenario.effective_tags:
        scenario.skip(reason="@no_prod scenario skipped in prod environment")
        return

    # Per-scenario state
    context.cleanup = CleanupRegistry()
    context._scenario_start = time.time()
    context._steps_recorded: list[StepReport] = []
    context._retry_attempt = context.__dict__.get("_retry_attempt", 0)

    # ---- UI ----
    if "ui" in scenario.effective_tags or scenario.feature.name.lower().startswith("ui"):
        scenario_video_dir = VIDEOS / scenario.name.replace(" ", "_")
        context.ctx = context.browser_factory.new_context(scenario.name, video_dir=scenario_video_dir)
        context.page = context.browser_factory.new_page(context.ctx)
        context.cleanup.add(lambda: context.ctx.close())

    # ---- API ----
    context.auth = AuthManager(context.cfg)
    if "api" in scenario.effective_tags or "rest" in scenario.effective_tags:
        context.rest = RestClient(context.cfg, auth=context.auth)
        context.cleanup.add(context.rest.close)
    if "graphql" in scenario.effective_tags:
        context.graphql = GraphQLClient(context.cfg, auth=context.auth)
    if "grpc" in scenario.effective_tags:
        context.grpc = GrpcClient(context.cfg, auth=context.auth).connect()
        context.cleanup.add(context.grpc.close)
    if "websocket" in scenario.effective_tags:
        context.ws = WebSocketClient(context.cfg, auth=context.auth)
        context.cleanup.add(context.ws.close)
    if "kafka" in scenario.effective_tags:
        context.kafka_producer = KafkaTestProducer(context.cfg).start()
        context.cleanup.add(context.kafka_producer.stop)

    # ---- Databases ----
    if "postgres" in scenario.effective_tags or "db" in scenario.effective_tags:
        context.pg = PostgresClient(context.cfg).connect()
        context.cleanup.add(context.pg.close)
    if "mysql" in scenario.effective_tags:
        context.mysql = MySQLClient(context.cfg).connect()
        context.cleanup.add(context.mysql.close)
    if "mongo" in scenario.effective_tags:
        context.mongo = MongoTestClient(context.cfg).connect()
        context.cleanup.add(context.mongo.close)
    if "dynamo" in scenario.effective_tags:
        context.dynamo = DynamoTestClient(context.cfg)


# --------------------------- before_step ---------------------------
def before_step(context, step):
    step._t0 = time.perf_counter()


# --------------------------- after_step ---------------------------
def after_step(context, step):
    duration_ms = (time.perf_counter() - getattr(step, "_t0", time.perf_counter())) * 1000
    err = None
    if step.status == "failed" and step.exception:
        err = "".join(traceback.format_exception(
            type(step.exception), step.exception, step.exc_traceback
        ))
        # UI screenshot on failure
        page = getattr(context, "page", None)
        if page and context.cfg.ui.screenshot_on_failure:
            try:
                shot = SCREENSHOTS / f"{context.scenario.name.replace(' ', '_')}.png"
                page.screenshot(path=str(shot), full_page=True)
                attach_screenshot(shot, "failure-screenshot")
            except Exception as e:
                log.warning(f"Could not capture screenshot: {e}")
    context._steps_recorded.append(
        StepReport(
            keyword=step.keyword, name=step.name, status=step.status.name,
            duration_ms=duration_ms, error=err,
        )
    )


# --------------------------- after_scenario ---------------------------
def after_scenario(context, scenario):
    # Stop tracing & save artifacts
    ctx = getattr(context, "ctx", None)
    if ctx is not None:
        try:
            trace_path = TRACES / f"{scenario.name.replace(' ', '_')}.zip"
            context.browser_factory.stop_trace(ctx, trace_path)
            if scenario.status.name == "failed":
                attach_trace(trace_path)
        except Exception as e:
            log.warning(f"Trace stop failed: {e}")
    page = getattr(context, "page", None)
    if page is not None and context.cfg.ui.record_video:
        try:
            video_path = page.video.path() if page.video else None
            if video_path and Path(video_path).exists():
                attach_video(Path(video_path))
        except Exception as e:
            log.warning(f"Video attach failed: {e}")

    # Cleanup hooks (DB, stubs, etc.)
    context.cleanup.run_all()

    # Retry failed scenarios once
    retry_attempt = context.__dict__.get("_retry_attempt", 0)
    if scenario.status.name == "failed" and retry_attempt < context.retry_failed:
        log.warning(f"Retrying scenario '{scenario.name}' (attempt {retry_attempt + 1})")
        context._retry_attempt = retry_attempt + 1
        scenario.reset()
        scenario.run(context._runner)  # re-run; Behave 1.2.6 supports manual rerun pattern

    # Append to Extent report
    duration_ms = (time.time() - context._scenario_start) * 1000
    context.reporter.add(
        ScenarioReport(
            feature=scenario.feature.name,
            name=scenario.name,
            tags=list(scenario.effective_tags),
            status=scenario.status.name,
            started_at=context._scenario_start,
            ended_at=time.time(),
            duration_ms=duration_ms,
            steps=context._steps_recorded,
        )
    )


# --------------------------- after_all ---------------------------
def after_all(context):
    try:
        out = context.reporter.finalize()
        log.info(f"Extent report: {out}")
        dash = render_dashboard()
        log.info(f"Custom dashboard: {dash}")
    except Exception as e:
        log.warning(f"Reporter finalize failed: {e}")
    finally:
        context.browser_factory.stop()
        log.info("QAForge finished.")
