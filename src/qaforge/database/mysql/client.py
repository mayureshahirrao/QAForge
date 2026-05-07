"""
qaforge.database.mysql.client
=============================
MySQL connector built on PyMySQL (DictCursor). Mirrors the PostgresClient
surface so tests can swap engines easily.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterable, List, Optional, Sequence

import pymysql
import pymysql.cursors

from qaforge.core.config_loader import Config, secret
from qaforge.core.logger import get_logger

log = get_logger(__name__)


class MySQLClient:
    def __init__(self, cfg: Config):
        self._spec = cfg.databases.mysql
        self._conn: Optional[pymysql.connections.Connection] = None

    def connect(self) -> "MySQLClient":
        self._conn = pymysql.connect(
            host=self._spec.host,
            port=self._spec.port,
            user=secret(self._spec.user_env),
            password=secret(self._spec.password_env),
            database=self._spec.db,
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
            charset="utf8mb4",
        )
        log.info("MySQL connected")
        return self

    @property
    def conn(self) -> pymysql.connections.Connection:
        if not self._conn:
            raise RuntimeError("MySQLClient.connect() not called")
        return self._conn

    def query(self, sql: str, params: Optional[Sequence[Any]] = None) -> List[dict]:
        with self.conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()

    def query_one(self, sql: str, params: Optional[Sequence[Any]] = None) -> Optional[dict]:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def execute(self, sql: str, params: Optional[Sequence[Any]] = None) -> int:
        with self.conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.rowcount

    def executemany(self, sql: str, seq: Iterable[Sequence[Any]]) -> None:
        with self.conn.cursor() as cur:
            cur.executemany(sql, list(seq))

    @contextmanager
    def txn(self):
        self.conn.begin()
        try:
            yield
            self.conn.rollback()
        except Exception:
            self.conn.rollback()
            raise

    def assert_row_count(self, table: str, where: str, params: Sequence[Any], expected: int) -> None:
        row = self.query_one(f"SELECT COUNT(*) AS c FROM {table} WHERE {where}", params)
        actual = row["c"] if row else 0
        assert actual == expected, f"MySQL row count mismatch on {table}: expected {expected}, got {actual}"

    def cleanup_test_rows(self, table: str, where: str, params: Sequence[Any]) -> int:
        n = self.execute(f"DELETE FROM {table} WHERE {where}", params)
        log.info(f"Cleaned {n} rows from {table}")
        return n

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
