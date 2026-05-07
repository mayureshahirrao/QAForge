"""
qaforge.reporting.extent_reporter
=================================
"Extent-style" JSON reporter — mirrors the structure of ExtentReports for
teams familiar with that format. The reporter is a singleton populated by
Behave hooks, and is dumped to `reports/extent/extent.json` after the run.

A companion HTML renderer (`custom_dashboard.py`) consumes this JSON to
produce a static, shareable dashboard.
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

REPORTS_DIR = Path(__file__).resolve().parents[3] / "reports" / "extent"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class StepReport:
    keyword: str
    name: str
    status: str
    duration_ms: float
    error: Optional[str] = None


@dataclass
class ScenarioReport:
    feature: str
    name: str
    tags: List[str] = field(default_factory=list)
    status: str = "passed"
    started_at: float = 0.0
    ended_at: float = 0.0
    duration_ms: float = 0.0
    steps: List[StepReport] = field(default_factory=list)
    attachments: List[str] = field(default_factory=list)


@dataclass
class RunSummary:
    environment: str
    started_at: float = field(default_factory=time.time)
    ended_at: Optional[float] = None
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    scenarios: List[ScenarioReport] = field(default_factory=list)


class ExtentReporter:
    """Thread-safe singleton accumulator."""
    _instance: Optional["ExtentReporter"] = None
    _lock = threading.Lock()

    def __new__(cls, environment: str = "dev") -> "ExtentReporter":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.run = RunSummary(environment=environment)
            return cls._instance

    def add(self, scenario: ScenarioReport) -> None:
        with self._lock:
            self.run.scenarios.append(scenario)
            self.run.total += 1
            if scenario.status == "passed":
                self.run.passed += 1
            elif scenario.status == "failed":
                self.run.failed += 1
            else:
                self.run.skipped += 1

    def finalize(self) -> Path:
        with self._lock:
            self.run.ended_at = time.time()
            out = REPORTS_DIR / "extent.json"
            out.write_text(json.dumps(asdict(self.run), indent=2, default=str))
            return out

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self.run)
