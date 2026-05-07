"""
qaforge.database.mongo.client
=============================
MongoDB testing helper built on `pymongo`. Returns a typed wrapper around
the chosen database with cleanup-friendly helpers.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from qaforge.core.config_loader import Config, secret
from qaforge.core.logger import get_logger

log = get_logger(__name__)


class MongoTestClient:
    def __init__(self, cfg: Config):
        self._spec = cfg.databases.mongo
        self._client: Optional[MongoClient] = None
        self._db: Optional[Database] = None

    def connect(self) -> "MongoTestClient":
        self._client = MongoClient(secret(self._spec.uri_env), tz_aware=True)
        self._db = self._client[self._spec.db]
        log.info(f"Mongo connected to {self._spec.db}")
        return self

    @property
    def db(self) -> Database:
        if self._db is None:
            raise RuntimeError("MongoTestClient.connect() not called")
        return self._db

    def collection(self, name: str) -> Collection:
        return self.db[name]

    # ---------- helpers ----------
    def insert_one(self, col: str, doc: Dict[str, Any]) -> str:
        return str(self.collection(col).insert_one(doc).inserted_id)

    def find(self, col: str, filt: Optional[Dict[str, Any]] = None, limit: int = 100) -> List[Dict[str, Any]]:
        cursor = self.collection(col).find(filt or {}).limit(limit)
        return list(cursor)

    def count(self, col: str, filt: Optional[Dict[str, Any]] = None) -> int:
        return self.collection(col).count_documents(filt or {})

    def assert_doc_exists(self, col: str, filt: Dict[str, Any]) -> None:
        assert self.count(col, filt) > 0, f"No document in {col} matching {filt}"

    def cleanup(self, col: str, filt: Dict[str, Any]) -> int:
        n = self.collection(col).delete_many(filt).deleted_count
        log.info(f"Mongo cleanup: deleted {n} docs from {col}")
        return n

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
