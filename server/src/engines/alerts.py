"""
Alert engine: evaluates threshold-based alert rules against incoming telemetry.
Maintains per-(rule, agent) cooldowns in Redis to prevent alert spam.
"""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID

import redis.asyncio as redis

from ..config import get_settings
from ..db.models import Agent, AlertRules, Alerts
from ..db.repository.alertsRepo import AlertsRepository
from ..metrics.exporter import record_alert_fired
from ..realtime import broker
from ..schemas import ResourcesPayload

logger = logging.getLogger(__name__)

# Operators supported in alert rules
_OPERATORS = {
    "gt": lambda a, b: a > b,
    "ge": lambda a, b: a >= b,
    "lt": lambda a, b: a < b,
    "le": lambda a, b: a <= b,
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
}

# Map metric name -> extractor from ResourcesPayload
def _metric_value(metric: str, resources: ResourcesPayload) -> float | None:
    if metric == "cpu_pct" or metric == "cpu_percent":
        return resources.cpu_percent
    if metric == "mem_mb" or metric == "memory_mb":
        return resources.memory_mb
    if metric == "mem_pct" or metric == "memory_percent":
        if resources.memory_limit_mb > 0:
            return (resources.memory_mb / resources.memory_limit_mb) * 100.0
        return None
    if metric == "net_bytes_sent":
        return resources.net_bytes_sent
    if metric == "net_bytes_recv":
        return resources.net_bytes_recv
    if metric == "disk_read_bytes":
        return resources.disk_read_bytes
    if metric == "disk_write_bytes":
        return resources.disk_write_bytes
    return None


class AlertEngine:
    """Evaluates alert rules against telemetry. Uses Redis for cooldown state."""

    COOLDOWN_KEY = "containerguard:alert:cooldown"

    def __init__(self) -> None:
        self._redis: redis.Redis | None = None

    async def start(self) -> None:
        url = get_settings().redis_url
        if not url:
            logger.warning("alert engine running without redis — cooldowns disabled")
            return

        self._redis = redis.from_url(url, decode_responses=True)
        last_exc: Exception | None = None
        for attempt in range(10):
            try:
                await self._redis.ping()
                last_exc = None
                break
            except Exception as exc:
                last_exc = exc
                import asyncio as _asyncio
                logger.warning("alert engine redis ping failed (attempt %d/10): %s", attempt + 1, exc)
                await _asyncio.sleep(1.5)
        if last_exc is not None:
            self._redis = None
            logger.error("alert engine giving up on redis: %s", last_exc)
            return
        logger.info("alert engine connected to redis")

    async def stop(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    async def _is_cooled_down(self, rule_id: UUID, agent_id: UUID, cooldown_sec: int) -> bool:
        """Returns True if the alert is in cooldown (should be suppressed)."""
        if self._redis is None or cooldown_sec <= 0:
            return False
        key = f"{self.COOLDOWN_KEY}:{rule_id}:{agent_id}"
        existed = await self._redis.set(key, str(int(time.time())), ex=cooldown_sec, nx=True)
        # nx=True means SET only if not exists; returns True if set, None if already there
        return existed is None

    async def evaluate_resources(
        self,
        agent: Agent,
        resources: ResourcesPayload,
        repo: AlertsRepository,
    ) -> list[Alerts]:
        """Evaluate all enabled threshold rules against the given resources payload."""
        rules = await repo.list_rules(enabled_only=True)
        triggered: list[Alerts] = []

        for rule in rules:
            value = _metric_value(rule.metric, resources)
            if value is None:
                continue
            op = _OPERATORS.get(rule.operator)
            if op is None:
                continue
            if not op(value, rule.threshold):
                continue
            if await self._is_cooled_down(rule.id, agent.id, rule.cooldown_sec):
                continue

            message = (
                f"{rule.name}: {rule.metric} = {value:.2f} {rule.operator} {rule.threshold:.2f} "
                f"on {agent.hostname}"
            )
            alert = await repo.create_alert(
                agent_id=agent.id,
                rule_id=rule.id,
                rule_name=rule.name,
                severity=rule.severity,
                message=message,
                alert_metadata={
                    "metric": rule.metric,
                    "value": value,
                    "operator": rule.operator,
                    "threshold": rule.threshold,
                    "container_id": agent.container_id,
                    "hostname": agent.hostname,
                },
            )
            triggered.append(alert)
            logger.info("alert fired: %s", message)
            record_alert_fired(rule.severity, rule.name)
            await broker.publish_alert(_alert_to_dict(alert, agent))

        return triggered

    async def fire_custom(
        self,
        repo: AlertsRepository,
        *,
        agent: Agent,
        rule_name: str,
        severity: str,
        message: str,
        rule_id: UUID | None = None,
        cooldown_key: str | None = None,
        cooldown_sec: int = 60,
        metadata: dict[str, Any] | None = None,
    ) -> Alerts | None:
        """Fire an ad-hoc alert (used by anomaly + compliance engines)."""
        if cooldown_key is not None and self._redis is not None and cooldown_sec > 0:
            key = f"{self.COOLDOWN_KEY}:custom:{cooldown_key}:{agent.id}"
            existed = await self._redis.set(key, str(int(time.time())), ex=cooldown_sec, nx=True)
            if existed is None:
                return None

        # Always include agent context in metadata
        enriched_metadata = dict(metadata or {})
        enriched_metadata.setdefault("hostname", agent.hostname)
        enriched_metadata.setdefault("container_id", agent.container_id)

        alert = await repo.create_alert(
            agent_id=agent.id,
            rule_id=rule_id,
            rule_name=rule_name,
            severity=severity,
            message=message,
            alert_metadata=enriched_metadata,
        )
        logger.info("alert fired: %s", message)
        record_alert_fired(severity, rule_name)
        await broker.publish_alert(_alert_to_dict(alert, agent))
        return alert


def _alert_to_dict(alert: Alerts, agent: Agent) -> dict[str, Any]:
    return {
        "type": "alert",
        "id": str(alert.id),
        "agent_id": str(alert.agent_id),
        "hostname": agent.hostname,
        "container_id": agent.container_id,
        "rule_id": str(alert.rule_id) if alert.rule_id else None,
        "rule_name": alert.rule_name,
        "severity": alert.severity,
        "message": alert.message,
        "status": alert.status,
        "alert_metadata": alert.alert_metadata,
        "created_at": alert.created_at.isoformat() if alert.created_at else None,
    }


alert_engine = AlertEngine()
