"""
qaforge.utils.network
=====================
Helpers for Playwright network interception used in UI tests.
"""
from __future__ import annotations

from typing import Callable, Dict, List

from playwright.sync_api import Page, Request, Route


class NetworkRecorder:
    """Records all requests for the lifetime of a page."""

    def __init__(self, page: Page):
        self.page = page
        self.requests: List[Request] = []
        page.on("request", self._on_request)

    def _on_request(self, req: Request) -> None:
        self.requests.append(req)

    def filter(self, predicate: Callable[[Request], bool]) -> List[Request]:
        return [r for r in self.requests if predicate(r)]


def stub_route(page: Page, url_glob: str, status: int = 200,
               json_body: Dict | None = None, body: str | None = None) -> None:
    """Intercept and stub a network request matching `url_glob`."""

    def handler(route: Route) -> None:
        if json_body is not None:
            route.fulfill(status=status, json=json_body)
        else:
            route.fulfill(status=status, body=body or "")

    page.route(url_glob, handler)


def block_third_party(page: Page, allowed_hosts: List[str]) -> None:
    """Block any request whose host is not in `allowed_hosts`."""
    def handler(route: Route) -> None:
        host = route.request.url.split("/")[2]
        if any(host.endswith(h) for h in allowed_hosts):
            route.continue_()
        else:
            route.abort()

    page.route("**/*", handler)
