"""
qaforge.hooks.cleanup
=====================
Per-scenario cleanup registry. Steps register cleanup callables via
`context.cleanup.add(fn)`; they are executed LIFO in `after_scenario`.

This avoids polluting the database with test artifacts even when a scenario
fails midway.
"""
from __future__ import annotations

from typing import Callable, List

from qaforge.core.logger import get_logger

log = get_logger(__name__)


class CleanupRegistry:
    def __init__(self):
        self._stack: List[Callable[[], None]] = []

    def add(self, fn: Callable[[], None]) -> None:
        self._stack.append(fn)

    def run_all(self) -> None:
        while self._stack:
            fn = self._stack.pop()
            try:
                fn()
            except Exception as e:
                log.warning(f"Cleanup callable {fn!r} failed: {e}")
