"""
qaforge.api.async_api.kafka_client
==================================
Test helper for event-driven services using Kafka. Wraps `aiokafka` in a
synchronous façade so step definitions stay readable.

Pattern:
    producer = KafkaTestProducer(cfg).start()
    producer.send("orders.created", {"id": 1, "total": 99.99})
    producer.stop()

    consumer = KafkaTestConsumer(cfg, "orders.processed", group="qa-test").start()
    msgs = consumer.poll(expected=1, timeout_seconds=10)
    consumer.stop()
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from qaforge.core.config_loader import Config
from qaforge.core.logger import get_logger

log = get_logger(__name__)


class KafkaTestProducer:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._loop = asyncio.new_event_loop()
        self._producer: AIOKafkaProducer | None = None

    def start(self) -> "KafkaTestProducer":
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self.cfg.api.async_api.kafka_brokers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        self._loop.run_until_complete(self._producer.start())
        return self

    def send(self, topic: str, value: Dict[str, Any], key: str | None = None) -> None:
        assert self._producer
        self._loop.run_until_complete(
            self._producer.send_and_wait(topic, value, key=key.encode() if key else None)
        )
        log.debug(f"Sent to {topic}: {value!r}")

    def stop(self) -> None:
        if self._producer:
            self._loop.run_until_complete(self._producer.stop())
            self._producer = None
        self._loop.close()


class KafkaTestConsumer:
    def __init__(self, cfg: Config, topic: str, group: str = "qa-test"):
        self.cfg = cfg
        self.topic = topic
        self.group = group
        self._loop = asyncio.new_event_loop()
        self._consumer: AIOKafkaConsumer | None = None

    def start(self) -> "KafkaTestConsumer":
        self._consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=self.cfg.api.async_api.kafka_brokers,
            group_id=self.group,
            auto_offset_reset="latest",
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            enable_auto_commit=True,
        )
        self._loop.run_until_complete(self._consumer.start())
        return self

    def poll(self, expected: int, timeout_seconds: float = 10.0) -> List[Dict[str, Any]]:
        return self._loop.run_until_complete(self._poll(expected, timeout_seconds))

    async def _poll(self, expected: int, timeout: float) -> List[Dict[str, Any]]:
        assert self._consumer
        out: List[Dict[str, Any]] = []
        try:
            async with asyncio.timeout(timeout):
                async for msg in self._consumer:
                    out.append(msg.value)
                    if len(out) >= expected:
                        break
        except TimeoutError:
            log.warning(f"Kafka consumer timed out at {len(out)}/{expected} messages")
        return out

    def stop(self) -> None:
        if self._consumer:
            self._loop.run_until_complete(self._consumer.stop())
            self._consumer = None
        self._loop.close()
