"""
qaforge.database.postgres.client
================================
PostgreSQL connector built on `psycopg` (3.x). Provides:
- query(), execute() with parameter binding (NEVER use string formatting)
- transactional context (.txn()) for tests that must roll back
- helper assertions for read/write/consistency checks

Connection lifecycle: one connection per scenario. Closed in after_scenario.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterable, List, Optional, Sequence

import psycopg
from psycopg.rows import dict_row

from qaforge.core.config_loader import Config, secret
from qaforge.core.logger import get_logger

log = get_logger(__name__)


class PostgresClient:
    def __init__(self, cfg: Config):
        spec = cfg.databases.postgres
        self._dsn = (
            f"host={spec.host} port={spec.port} dbname={spec.db} "
            f"user={secret(spec.user_env)} password={secret(spec.password_env)}"
        )
        self._conn: Optional[psycopg.Connection] = None

    def connect(self) -> "PostgresClient":
        self._conn = psycopg.connect(self._dsn, row_factory=dict_row, autocommit=True)
        log.info("Postgres connected")
        return self

    @property
    def conn(self) -> psycopg.Connection:
        if not self._conn:
            raise RuntimeError("PostgresClient.connect() not called")
        return self._conn

    # ---------- queries ----------
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

    # ---------- transactional helper ----------
    @contextmanager
    def txn(self):
        """Run statements in a transaction that rolls back on exit (great for read-only assertions)."""
        self.conn.autocommit = False
        try:
            yield
            self.conn.rollback()
        except Exception:
            self.conn.rollback()
            raise
        finally:
            self.conn.autocommit = True

    # ---------- assertions / cleanup ----------
    def assert_row_count(self, table: str, where: str, params: Sequence[Any], expected: int) -> None:
        # `table` and `where` are NEVER user-supplied; tests author them.
        row = self.query_one(f"SELECT COUNT(*) AS c FROM {table} WHERE {where}", params)
        actual = row["c"] if row else 0
        assert actual == expected, f"Postgres row count mismatch on {table}: expected {expected}, got {actual}"

    def cleanup_test_rows(self, table: str, where: str, params: Sequence[Any]) -> int:
        n = self.execute(f"DELETE FROM {table} WHERE {where}", params)
        log.info(f"Cleaned {n} rows from {table}")
        return n

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
