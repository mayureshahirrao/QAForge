"""
qaforge.core.browser_factory
============================
Centralised Playwright browser/context/page lifecycle.

Why a factory?
- Behave hooks (`before_scenario`, `after_scenario`) call methods here so test
  authors never touch sync_playwright() directly.
- One place to enable trace, video, and viewport — overridable via config.
- Supports parallel scenarios — each Behave worker gets its own Playwright
  instance (the worker process is the unit of isolation).
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

from qaforge.core.config_loader import Config


class BrowserFactory:
    """Owns Playwright and produces fresh contexts per scenario."""

    def __init__(self, cfg: Config, browser_name: str = "chromium", headless: bool = True):
        self.cfg = cfg
        self.browser_name = browser_name
        self.headless = headless
        self._pw: Optional[Playwright] = None
        self._browser: Optional[Browser] = None

    # -------- lifecycle --------
    def start(self) -> None:
        self._pw = sync_playwright().start()
        launcher = getattr(self._pw, self.browser_name)
        self._browser = launcher.launch(
            headless=self.headless,
            slow_mo=self.cfg.ui.slow_mo_ms,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )

    def stop(self) -> None:
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._pw:
            self._pw.stop()
            self._pw = None

    # -------- per-scenario context --------
    def new_context(self, scenario_name: str, video_dir: Optional[Path] = None) -> BrowserContext:
        if not self._browser:
            raise RuntimeError("BrowserFactory.start() must be called first")
        kwargs = dict(
            viewport=self.cfg.ui.viewport,
            locale=self.cfg.ui.locale,
            timezone_id=self.cfg.ui.timezone,
            ignore_https_errors=True,
        )
        if self.cfg.ui.record_video and video_dir:
            kwargs["record_video_dir"] = str(video_dir)
            kwargs["record_video_size"] = self.cfg.ui.viewport
        ctx = self._browser.new_context(**kwargs)
        ctx.set_default_timeout(self.cfg.ui.default_timeout_ms)
        ctx.set_default_navigation_timeout(self.cfg.ui.navigation_timeout_ms)
        if self.cfg.ui.trace != "off":
            ctx.tracing.start(screenshots=True, snapshots=True, sources=True)
        return ctx

    def new_page(self, ctx: BrowserContext) -> Page:
        page = ctx.new_page()
        return page

    def stop_trace(self, ctx: BrowserContext, trace_path: Path) -> None:
        if self.cfg.ui.trace != "off":
            trace_path.parent.mkdir(parents=True, exist_ok=True)
            ctx.tracing.stop(path=str(trace_path))
