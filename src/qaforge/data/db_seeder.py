"""
qaforge.data.db_seeder
======================
Seed databases with known test fixtures before suites run, then clean up.

Each seeder reads from `test_data/static/seed_<engine>.json` and uses the
corresponding DB client.  Seeders are idempotent — re-running re-inserts only
missing rows.
"""
from __future__ import annotations

from typing import Any, Dict, List

from qaforge.core.config_loader import Config
from qaforge.core.logger import get_logger
from qaforge.data.loaders import load_json
from qaforge.database.dynamo.client import DynamoTestClient
from qaforge.database.mongo.client import MongoTestClient
from qaforge.database.mysql.client import MySQLClient
from qaforge.database.postgres.client import PostgresClient

log = get_logger(__name__)


class DBSeeder:
    def __init__(self, cfg: Config):
        self.cfg = cfg

    # -------- per-engine seeders --------
    def seed_postgres(self) -> None:
        data: Dict[str, List[Dict[str, Any]]] = load_json("static/seed_postgres.json")
        pg = PostgresClient(self.cfg).connect()
        try:
            for table, rows in data.items():
                for row in rows:
                    cols = ", ".join(row.keys())
                    placeholders = ", ".join(["%s"] * len(row))
                    pg.execute(
                        f"INSERT INTO {table} ({cols}) VALUES ({placeholders}) ON CONFLICT DO NOTHING",
                        list(row.values()),
                    )
                log.info(f"[seed:postgres] {table}: {len(rows)} rows")
        finally:
            pg.close()

    def seed_mysql(self) -> None:
        data = load_json("static/seed_mysql.json")
        my = MySQLClient(self.cfg).connect()
        try:
            for table, rows in data.items():
                for row in rows:
                    cols = ", ".join(row.keys())
                    placeholders = ", ".join(["%s"] * len(row))
                    my.execute(
                        f"INSERT IGNORE INTO {table} ({cols}) VALUES ({placeholders})",
                        list(row.values()),
                    )
                log.info(f"[seed:mysql] {table}: {len(rows)} rows")
        finally:
            my.close()

    def seed_mongo(self) -> None:
        data = load_json("static/seed_mongo.json")
        mongo = MongoTestClient(self.cfg).connect()
        try:
            for col, docs in data.items():
                for doc in docs:
                    mongo.collection(col).update_one(
                        {"_id": doc["_id"]}, {"$set": doc}, upsert=True
                    )
                log.info(f"[seed:mongo] {col}: {len(docs)} docs")
        finally:
            mongo.close()

    def seed_dynamo(self) -> None:
        data = load_json("static/seed_dynamo.json")
        dyn = DynamoTestClient(self.cfg)
        for table, items in data.items():
            for item in items:
                dyn.put_item(table, item)
            log.info(f"[seed:dynamo] {table}: {len(items)} items")

    def seed_all(self) -> None:
        for fn in (self.seed_postgres, self.seed_mysql, self.seed_mongo, self.seed_dynamo):
            try:
                fn()
            except FileNotFoundError as e:
                log.warning(f"Skipping seeder: {e}")
            except Exception as e:
                log.error(f"Seeder {fn.__name__} failed: {e}")
