"""
qaforge.pages.base_page
=======================
BasePage — every page object inherits from this.

Conventions:
- Locators are defined as `@property` returning Playwright `Locator` objects.
- Actions (click, fill) belong to the page; assertions live in steps or
  dedicated assertion helpers.
- Never sleep — use Playwright auto-waiting (`expect(...)`).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from playwright.sync_api import Page, Response, expect

from qaforge.core.logger import get_logger

log = get_logger(__name__)


class BasePage:
    """Common building block for every page object."""

    URL_PATH: str = "/"  # override per page

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url.rstrip("/")

    # ---------- navigation ----------
    def open(self, query: Optional[Dict[str, Any]] = None) -> Optional[Response]:
        url = f"{self.base_url}{self.URL_PATH}"
        if query:
            qs = "&".join(f"{k}={v}" for k, v in query.items())
            url = f"{url}?{qs}"
        log.info(f"Navigating to {url}")
        return self.page.goto(url, wait_until="domcontentloaded")

    def reload(self) -> None:
        self.page.reload(wait_until="domcontentloaded")

    # ---------- generic helpers ----------
    def screenshot(self, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=str(dest), full_page=True)
        log.debug(f"Screenshot saved: {dest}")

    def expect_visible(self, locator, timeout_ms: int = 10000) -> None:
        expect(locator).to_be_visible(timeout=timeout_ms)

    def expect_text(self, locator, text: str, timeout_ms: int = 10000) -> None:
        expect(locator).to_contain_text(text, timeout=timeout_ms)

    def expect_url(self, pattern: str, timeout_ms: int = 10000) -> None:
        expect(self.page).to_have_url(pattern, timeout=timeout_ms)
