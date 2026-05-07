"""
qaforge.data.loaders
====================
Loaders for external test data: CSV, JSON, and YAML.

Conventions:
- All paths resolved relative to repo-root `test_data/`.
- CSV is parsed into a list of dicts (DictReader).
- JSON returned as parsed object.
- All loaders are cached (LRU) to avoid re-reading on every call.
"""
from __future__ import annotations

import csv
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

import yaml

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "test_data"


@lru_cache(maxsize=64)
def load_json(rel_path: str) -> Any:
    fp = DATA_DIR / rel_path
    return json.loads(fp.read_text(encoding="utf-8"))


@lru_cache(maxsize=64)
def load_yaml(rel_path: str) -> Any:
    fp = DATA_DIR / rel_path
    return yaml.safe_load(fp.read_text(encoding="utf-8"))


def load_csv(rel_path: str) -> List[Dict[str, str]]:
    fp = DATA_DIR / rel_path
    with fp.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def static_user(key: str) -> Dict[str, Any]:
    """Return a known static user from `test_data/static/users.json` by key."""
    users = load_json("static/users.json")
    if key not in users:
        raise KeyError(f"Static user '{key}' not found. Available: {list(users.keys())}")
    return users[key]
