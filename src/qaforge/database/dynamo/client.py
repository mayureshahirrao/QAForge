"""
qaforge.database.dynamo.client
==============================
DynamoDB test helper built on `boto3`. Uses the high-level resource API for
ergonomic Python-native types. Supports local DynamoDB (via endpoint) and
real AWS (region-only).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import boto3
from boto3.dynamodb.conditions import Attr, Key

from qaforge.core.config_loader import Config
from qaforge.core.logger import get_logger

log = get_logger(__name__)


class DynamoTestClient:
    def __init__(self, cfg: Config):
        spec = cfg.databases.dynamo
        kwargs: Dict[str, Any] = {"region_name": spec.region}
        if spec.endpoint:
            kwargs["endpoint_url"] = spec.endpoint
        self._resource = boto3.resource("dynamodb", **kwargs)
        log.info(f"Dynamo client built (region={spec.region}, endpoint={spec.endpoint or 'AWS'})")

    def table(self, name: str):
        return self._resource.Table(name)

    # ---------- read/write ----------
    def put_item(self, table: str, item: Dict[str, Any]) -> None:
        self.table(table).put_item(Item=item)

    def get_item(self, table: str, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        resp = self.table(table).get_item(Key=key)
        return resp.get("Item")

    def query(self, table: str, key_name: str, key_value: Any) -> List[Dict[str, Any]]:
        resp = self.table(table).query(KeyConditionExpression=Key(key_name).eq(key_value))
        return resp.get("Items", [])

    def scan_filter(self, table: str, attr_name: str, attr_value: Any) -> List[Dict[str, Any]]:
        resp = self.table(table).scan(FilterExpression=Attr(attr_name).eq(attr_value))
        return resp.get("Items", [])

    # ---------- assertions / cleanup ----------
    def assert_item_exists(self, table: str, key: Dict[str, Any]) -> None:
        assert self.get_item(table, key), f"Dynamo item missing in {table}: {key}"

    def cleanup(self, table: str, keys: List[Dict[str, Any]]) -> int:
        with self.table(table).batch_writer() as batch:
            for k in keys:
                batch.delete_item(Key=k)
        log.info(f"Dynamo cleanup: removed {len(keys)} items from {table}")
        return len(keys)
