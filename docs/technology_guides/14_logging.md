# 14 — Logging Frameworks (Loguru + stdlib)

> **Source files:** `src/qaforge/core/logger.py`.

---

## 1. The dual-logger problem

Most Python codebases use the standard `logging` module. Most modern apps prefer `loguru` for ergonomics. QAForge uses both — *correctly*:

- **`loguru`** is the developer-facing logger with colours, structured rotation, and zero-config sinks.
- **stdlib `logging`** is what every library you don't control (Playwright, requests, boto3, psycopg, …) emits to.

If you only configure loguru, library logs go to a separate, ugly stderr handler. If you only use stdlib, you lose ergonomic formatting. The fix: **bridge the two.**

---

## 2. The bridge — `InterceptHandler`

```python
class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = _logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        _logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())
```

This handler intercepts every stdlib log record and re-emits it through loguru. The frame walking preserves `filename:lineno` accuracy so the source location in your logs is the *real* call site, not the handler.

`configure_logging()` then installs `InterceptHandler` as the **only** stdlib handler:

```python
logging.basicConfig(handlers=[InterceptHandler()], level=level, force=True)
```

After this, `logging.getLogger("anything").info("hi")` shows up in loguru's coloured stdout and zipped file sink.

---

## 3. Sinks configured by default

```python
_logger.add(sys.stdout,
            level="INFO",
            colorize=True,
            format="<green>{time:HH:mm:ss}</green> | <lvl>{level:<7}</lvl> | "
                   "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - {message}")

_logger.add(LOG_DIR / "qaforge.log",
            level="DEBUG",
            rotation="10 MB",
            retention="14 days",
            compression="zip",
            enqueue=True,
            backtrace=True,
            diagnose=False)
```

- **stdout**: human-readable, INFO+, colourised.
- **file**: full DEBUG, rotated at 10 MB, kept 14 days, compressed to zip, **enqueued** (thread/process safe — important under behavex parallelism), tracebacks on, **diagnose off** (so secrets in locals are never dumped).

---

## 4. Usage

```python
from qaforge.core.logger import get_logger
log = get_logger(__name__)

log.info("Login starting for {email}", email=user.email)
log.warning("Retry {n} for {url}", n=2, url=path)
log.exception("Unexpected DB error")     # automatically attaches traceback
```

Loguru format strings use `{name}` placeholders — fast, lazy, and avoids string formatting on disabled levels.

---

## 5. Noisy libraries — turn down the volume

```python
for noisy in ("urllib3", "asyncio", "websockets.client"):
    logging.getLogger(noisy).setLevel(logging.WARNING)
```

Add to this list any library that floods DEBUG. The setting takes effect on the **stdlib** logger object — but because of the bridge, it also affects what loguru emits.

---

## 6. Log levels — when to use each

- **DEBUG.** API request/response details, SQL with bound parameters (without secrets), browser action timings. Local-dev and CI-failure debugging.
- **INFO.** Test lifecycle: scenario start, browser launched, DB connected, token obtained.
- **WARNING.** Retries, fallback paths, missing optional config.
- **ERROR.** A test fails for an environmental reason (DB unreachable). Use `log.exception` to include traceback.
- **CRITICAL.** Reserved for "the framework itself is broken" — extremely rare.

---

## 7. Structured logging

If your downstream log aggregator (Datadog, Splunk, ELK) prefers JSON, swap the format on the file sink:

```python
_logger.add(LOG_DIR / "qaforge.jsonl",
            level="INFO",
            serialize=True,             # JSONL output
            rotation="10 MB",
            enqueue=True)
```

Each line becomes a JSON object with timestamp, level, name, message, and any keyword arguments you passed to `log.info(...)`.

---

## 8. Best practices

- **Never log a password, OTP, or token.** loguru's `diagnose=False` already suppresses local-variable dumps; don't undo that with `log.info(f"token={token}")`.
- **One logger per module:** `log = get_logger(__name__)` at the top.
- **Log keyword arguments, not f-strings.** `log.info("user {id}", id=u.id)` is faster (lazy) than `log.info(f"user {u.id}")`.
- **Use `log.exception()` in `except:` blocks.** It captures the active traceback automatically.
