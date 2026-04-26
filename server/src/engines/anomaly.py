"""
Anomaly detection engine: maintains rolling windows in Redis and flags
metrics that deviate >2 standard deviations from the rolling mean (Z-score).
"""

from __future__ import annotations

import json
import logging
import math
import time
from typing import Any

import redis.asyncio as redis

from ..config import get_settings
from ..db.models import Agent
from ..db.repository.alertsRepo import AlertsRepository
from ..schemas import ResourcesPayload
from .alerts import alert_engine

logger = logging.getLogger(__name__)

# Metrics tracked for anomaly detection
TRACKED_METRICS = ("cpu_pct", "mem_mb")
WINDOW_SIZE = 30           # last N samples
WINDOW_TTL_SEC = 1800      # 30 min, prevents stale data accumulating
Z_THRESHOLD = 2.5          # alert when |z| > 2.5
MIN_SAMPLES = 8            # need at least N samples to evaluate


class AnomalyEngine:
    KEY_PREFIX = "containerguard:anomaly"

    def __init__(self) -> None:
        self._redis: redis.Redis | None = None

    async def start(self) -> None:
        url = get_settings().redis_url
        if not url:
            return
        import asyncio as _asyncio
        self._redis = redis.from_url(url, decode_responses=True)
        for attempt in range(10):
            try:
                await self._redis.ping()
                logger.info("anomaly engine connected to redis")
                return
            except Exception as exc:
                logger.warning("anomaly engine redis ping failed (attempt %d/10): %s", attempt + 1, exc)
                await _asyncio.sleep(1.5)
        # Give up but don't crash startup
        self._redis = None
        logger.error("anomaly engine giving up on redis")

    async def stop(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    def _key(self, agent_id: str, metric: str) -> str:
        return f"{self.KEY_PREFIX}:{agent_id}:{metric}"

    async def evaluate(
        self,
        agent: Agent,
        resources: ResourcesPayload,
        repo: AlertsRepository,
    ) -> None:
        if self._redis is None:
            return

        for metric in TRACKED_METRICS:
            value = _extract(resources, metric)
            if value is None:
                continue

            key = self._key(str(agent.id), metric)
            # Push sample, trim to window, set TTL
            await self._redis.rpush(key, json.dumps({"v": value, "t": time.time()}))
            await self._redis.ltrim(key, -WINDOW_SIZE, -1)
            await self._redis.expire(key, WINDOW_TTL_SEC)

            # Read window
            raw = await self._redis.lrange(key, 0, -1)
            samples = [json.loads(s)["v"] for s in raw]
            if len(samples) < MIN_SAMPLES:
                continue

            history = samples[:-1]  # exclude current sample for baseline
            mean = sum(history) / len(history)
            variance = sum((x - mean) ** 2 for x in history) / len(history)
            std = math.sqrt(variance)
            if std < 1e-6:
                continue

            z = (value - mean) / std
            if abs(z) <= Z_THRESHOLD:
                continue

            severity = "high" if abs(z) > 4 else "medium"
            direction = "spike" if z > 0 else "drop"
            message = (
                f"Anomaly: {metric} {direction} on {agent.hostname} — "
                f"value={value:.2f} mean={mean:.2f} z={z:.2f}"
            )
            await alert_engine.fire_custom(
                repo,
                agent=agent,
                rule_name=f"anomaly:{metric}",
                severity=severity,
                message=message,
                cooldown_key=f"anomaly:{metric}",
                cooldown_sec=120,
                metadata={
                    "type": "anomaly",
                    "metric": metric,
                    "value": value,
                    "mean": mean,
                    "std": std,
                    "z_score": z,
                    "samples": len(history),
                },
            )


def _extract(resources: ResourcesPayload, metric: str) -> float | None:
    if metric == "cpu_pct":
        return resources.cpu_percent
    if metric == "mem_mb":
        return resources.memory_mb
    return None


anomaly_engine = AnomalyEngine()
