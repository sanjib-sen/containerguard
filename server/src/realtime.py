from __future__ import annotations

import asyncio
import json
import logging
from contextlib import suppress
from typing import Any

import redis.asyncio as redis

from .api.websocket import manager
from .config import get_settings

logger = logging.getLogger(__name__)

_DASHBOARD_CHANNEL = "containerguard:ws:dashboard"
_ALERTS_CHANNEL = "containerguard:ws:alerts"


class RedisWebSocketBroker:
    def __init__(self) -> None:
        self._publisher: redis.Redis | None = None
        self._subscriber: redis.Redis | None = None
        self._subscription_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        redis_url = get_settings().redis_url
        if not redis_url:
            raise RuntimeError("REDIS_URL must be configured for Redis-backed websocket fan-out")

        self._publisher = redis.from_url(redis_url, decode_responses=True)
        self._subscriber = redis.from_url(redis_url, decode_responses=True)

        # Retry the initial ping — Redis service may not be DNS-resolvable for the
        # first few seconds even when its healthcheck is green inside the Docker
        # network on a cold start.
        last_exc: Exception | None = None
        for attempt in range(10):
            try:
                await self._publisher.ping()
                await self._subscriber.ping()
                last_exc = None
                break
            except Exception as exc:
                last_exc = exc
                logger.warning("redis ping failed (attempt %d/10): %s", attempt + 1, exc)
                await asyncio.sleep(1.5)
        if last_exc is not None:
            raise last_exc

        self._subscription_task = asyncio.create_task(self._run_subscription_loop())
        logger.info("started Redis websocket broker using %s", redis_url)

    async def stop(self) -> None:
        if self._subscription_task is not None:
            self._subscription_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._subscription_task
            self._subscription_task = None

        if self._publisher is not None:
            await self._publisher.aclose()
            self._publisher = None

        if self._subscriber is not None:
            await self._subscriber.aclose()
            self._subscriber = None

    async def publish_dashboard(self, data: dict[str, Any]) -> None:
        await self._publish(_DASHBOARD_CHANNEL, data)

    async def publish_alert(self, data: dict[str, Any]) -> None:
        await self._publish(_ALERTS_CHANNEL, data)

    async def _publish(self, channel: str, data: dict[str, Any]) -> None:
        if self._publisher is None:
            raise RuntimeError("Redis websocket broker is not started")
        await self._publisher.publish(channel, json.dumps(data))

    async def _run_subscription_loop(self) -> None:
        if self._subscriber is None:
            return

        while True:
            try:
                async with self._subscriber.pubsub() as pubsub:
                    await pubsub.subscribe(_DASHBOARD_CHANNEL, _ALERTS_CHANNEL)
                    while True:
                        message = await pubsub.get_message(
                            ignore_subscribe_messages=True,
                            timeout=None,
                        )
                        if message is None:
                            continue
                        await self._dispatch_message(message)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Redis websocket subscription loop failed; retrying")
                await asyncio.sleep(1)

    async def _dispatch_message(self, message: dict[str, Any]) -> None:
        channel = message.get("channel")
        raw_data = message.get("data")
        if not isinstance(channel, str) or not isinstance(raw_data, str):
            logger.warning("ignoring malformed Redis pubsub message: %r", message)
            return

        try:
            data = json.loads(raw_data)
        except json.JSONDecodeError:
            logger.warning("ignoring non-JSON Redis pubsub payload on %s", channel)
            return

        if not isinstance(data, dict):
            logger.warning("ignoring unexpected Redis pubsub payload on %s", channel)
            return

        if channel == _DASHBOARD_CHANNEL:
            await manager.broadcast_dashboard(data)
        elif channel == _ALERTS_CHANNEL:
            await manager.broadcast_alert(data)


broker = RedisWebSocketBroker()
