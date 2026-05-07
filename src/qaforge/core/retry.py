"""
qaforge.core.retry
==================
Reusable retry decorator built on `tenacity`. Use sparingly — prefer
explicit Playwright `expect()` waits over retrying.
"""
from __future__ import annotations

from typing import Callable, Tuple, Type

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from qaforge.core.logger import get_logger

log = get_logger(__name__)


def retry_on(
    exceptions: Tuple[Type[BaseException], ...] = (Exception,),
    attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
) -> Callable:
    """Decorator: retry on listed exceptions with exponential backoff."""

    def _wrap(fn: Callable) -> Callable:
        return retry(
            reraise=True,
            stop=stop_after_attempt(attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            retry=retry_if_exception_type(exceptions),
            before_sleep=lambda rs: log.warning(
                f"Retrying {fn.__name__} (attempt {rs.attempt_number}) after {rs.outcome.exception()!r}"
            ),
        )(fn)

    return _wrap
