"""
qaforge.api.rest.client
=======================
Thin, typed wrapper around `httpx.Client` for REST testing.

Design notes:
- One `RestClient` instance per scenario (created in environment.py).
- Auth is injected via `AuthManager` — never hard-coded.
- All requests log structured info (method, url, status, elapsed_ms) at DEBUG.
- 4xx/5xx are NOT auto-raised — tests assert explicitly so negative cases work.
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional

import httpx

from qaforge.api.auth_manager import AuthManager, AuthToken
from qaforge.core.config_loader import Config
from qaforge.core.logger import get_logger

log = get_logger(__name__)


class RestClient:
    def __init__(self, cfg: Config, auth: Optional[AuthManager] = None):
        self.cfg = cfg
        self.auth = auth
        self._client = httpx.Client(
            base_url=cfg.api.rest.base_url,
            timeout=cfg.api.rest.timeout_seconds,
            headers={"User-Agent": "QAForge/1.0", "Accept": "application/json"},
        )
        self._token: Optional[AuthToken] = None

    # ---------- auth ----------
    def with_oauth(self, scope: Optional[str] = None) -> "RestClient":
        assert self.auth, "AuthManager not configured"
        self._token = self.auth.oauth_token(scope=scope)
        return self

    def with_password_otp(self, email: str, password: str, otp: str) -> "RestClient":
        assert self.auth, "AuthManager not configured"
        self._token = self.auth.password_otp_token(email, password, otp)
        return self

    def with_role(self, role: str) -> "RestClient":
        assert self.auth, "AuthManager not configured"
        self._token = self.auth.assume_role(role)
        return self

    def clear_auth(self) -> "RestClient":
        self._token = None
        return self

    # ---------- request ----------
    def _headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        if self._token:
            headers.update(self._token.header)
        if extra:
            headers.update(extra)
        return headers

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        kwargs["headers"] = self._headers(kwargs.pop("headers", None))
        start = time.perf_counter()
        resp = self._client.request(method, path, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000
        log.debug(f"{method} {path} -> {resp.status_code} in {elapsed:.0f}ms")
        return resp

    def get(self, path: str, **kw) -> httpx.Response:
        return self._request("GET", path, **kw)

    def post(self, path: str, **kw) -> httpx.Response:
        return self._request("POST", path, **kw)

    def put(self, path: str, **kw) -> httpx.Response:
        return self._request("PUT", path, **kw)

    def patch(self, path: str, **kw) -> httpx.Response:
        return self._request("PATCH", path, **kw)

    def delete(self, path: str, **kw) -> httpx.Response:
        return self._request("DELETE", path, **kw)

    def head(self, path: str, **kw) -> httpx.Response:
        return self._request("HEAD", path, **kw)

    def close(self) -> None:
        self._client.close()
