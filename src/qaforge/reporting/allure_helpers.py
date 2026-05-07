"""
qaforge.reporting.allure_helpers
================================
Allure attachment helpers. The `allure-behave` formatter is wired through
`behave.ini` ([behave.formatters]) — these helpers add screenshots, videos,
trace files, and arbitrary text/JSON to the active scenario report.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import allure
from allure_commons.types import AttachmentType


def attach_screenshot(path: Path, name: str = "screenshot") -> None:
    if path and path.exists():
        allure.attach.file(str(path), name=name, attachment_type=AttachmentType.PNG)


def attach_video(path: Path, name: str = "video") -> None:
    if path and path.exists():
        allure.attach.file(str(path), name=name, attachment_type=AttachmentType.WEBM)


def attach_trace(path: Path, name: str = "playwright-trace.zip") -> None:
    if path and path.exists():
        allure.attach.file(
            str(path), name=name, attachment_type=AttachmentType.ZIP, extension="zip"
        )


def attach_json(payload: Any, name: str = "payload") -> None:
    allure.attach(
        json.dumps(payload, indent=2, default=str), name=name, attachment_type=AttachmentType.JSON
    )


def attach_text(text: str, name: str = "log") -> None:
    allure.attach(text, name=name, attachment_type=AttachmentType.TEXT)
