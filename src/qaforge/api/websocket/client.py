"""
qaforge.api.websocket.client
============================
Synchronous WebSocket helper using the `websockets` library wrapped in an
asyncio event loop runner. Sync API keeps Behave step files simple.

Use cases:
- Subscribe to live events
- Send messages and assert echo
- Test reconnection scenarios
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional

import websockets

from qaforge.api.auth_manager import AuthManager, AuthToken
from qaforge.core.config_loader import Config
from qaforge.core.logger import get_logger

log = get_logger(__name__)


class WebSocketClient:
    def __init__(self, cfg: Config, auth: Optional[AuthManager] = None):
        self.cfg = cfg
        self.auth = auth
        self.url = cfg.api.websocket.url
        self._token: Optional[AuthToken] = None
        self._loop = asyncio.new_event_loop()

    def with_oauth(self, scope: Optional[str] = None) -> "WebSocketClient":
        assert self.auth
        self._token = self.auth.oauth_token(scope=scope)
        return self

    def _headers(self) -> Optional[Dict[str, str]]:
        return self._token.header if self._token else None

    # ---------- sync API ----------
    def send_and_receive(self, message: Dict[str, Any], expect_messages: int = 1,
                         timeout_seconds: float = 10.0) -> List[Dict[str, Any]]:
        """Connect, send a JSON message, collect N replies, then close."""
        return self._loop.run_until_complete(
            self._send_and_receive(message, expect_messages, timeout_seconds)
        )

    async def _send_and_receive(self, message, n, timeout):
        async with websockets.connect(self.url, additional_headers=self._headers()) as ws:
            await ws.send(json.dumps(message))
            received: List[Dict[str, Any]] = []
            try:
                for _ in range(n):
                    raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
                    received.append(json.loads(raw) if raw.startswith("{") or raw.startswith("[")
                                    else {"raw": raw})
            except asyncio.TimeoutError:
                log.warning(f"WS timed out after {len(received)}/{n} messages")
            return received

    def stream(self, send_message: Dict[str, Any], duration_seconds: float = 5.0) -> List[Dict[str, Any]]:
        """Stream messages for a fixed duration after sending one initial message."""
        return self._loop.run_until_complete(self._stream(send_message, duration_seconds))

    async def _stream(self, msg, duration):
        async with websockets.connect(self.url, additional_headers=self._headers()) as ws:
            await ws.send(json.dumps(msg))
            received: List[Dict[str, Any]] = []
            end = self._loop.time() + duration
            while self._loop.time() < end:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=max(0.1, end - self._loop.time()))
                    received.append(json.loads(raw))
                except asyncio.TimeoutError:
                    break
            return received

    def close(self) -> None:
        self._loop.close()
