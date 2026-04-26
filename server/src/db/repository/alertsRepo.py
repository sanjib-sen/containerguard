from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Alerts, AlertRules


class AlertsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ── Alert CRUD ─────────────────────────────────────────────

    async def create_alert(
        self,
        *,
        agent_id: UUID,
        rule_name: str,
        severity: str,
        message: str,
        rule_id: UUID | None = None,
        alert_metadata: dict[str, Any] | None = None,
    ) -> Alerts:
        alert = Alerts(
            agent_id=agent_id,
            rule_id=rule_id,
            rule_name=rule_name,
            severity=severity,
            message=message,
            status="open",
            alert_metadata=alert_metadata,
        )
        self.session.add(alert)
        await self.session.commit()
        await self.session.refresh(alert)
        return alert

    async def list_alerts(
        self,
        *,
        agent_id: UUID | None = None,
        status: str | None = None,
        severity: str | None = None,
        limit: int = 200,
    ) -> list[Alerts]:
        statement = select(Alerts)
        if agent_id is not None:
            statement = statement.where(Alerts.agent_id == agent_id)
        if status is not None:
            statement = statement.where(Alerts.status == status)
        if severity is not None:
            statement = statement.where(Alerts.severity == severity)
        statement = statement.order_by(Alerts.created_at.desc()).limit(limit)
        result = await self.session.scalars(statement)
        return list(result)

    async def get_alert(self, alert_id: UUID) -> Alerts | None:
        return await self.session.get(Alerts, alert_id)

    async def set_alert_status(self, alert_id: UUID, status: str) -> Alerts | None:
        alert = await self.get_alert(alert_id)
        if alert is None:
            return None
        now = datetime.now(timezone.utc)
        alert.status = status
        if status == "acknowledged":
            alert.acknowledged_at = now
        elif status == "resolved":
            alert.resolved_at = now
        elif status == "open":
            alert.acknowledged_at = None
            alert.resolved_at = None
        await self.session.commit()
        await self.session.refresh(alert)
        return alert

    # ── Alert Rules CRUD ───────────────────────────────────────

    async def list_rules(self, *, enabled_only: bool = False) -> list[AlertRules]:
        statement = select(AlertRules)
        if enabled_only:
            statement = statement.where(AlertRules.enabled == True)  # noqa: E712
        result = await self.session.scalars(statement)
        return list(result)

    async def get_rule(self, rule_id: UUID) -> AlertRules | None:
        return await self.session.get(AlertRules, rule_id)

    async def create_rule(
        self,
        *,
        name: str,
        description: str | None,
        metric: str,
        operator: str,
        threshold: float,
        severity: str,
        cooldown_sec: int,
        enabled: bool = True,
    ) -> AlertRules:
        rule = AlertRules(
            name=name,
            description=description,
            metric=metric,
            operator=operator,
            threshold=threshold,
            severity=severity,
            cooldown_sec=cooldown_sec,
            enabled=enabled,
        )
        self.session.add(rule)
        await self.session.commit()
        await self.session.refresh(rule)
        return rule

    async def update_rule(self, rule_id: UUID, **fields: Any) -> AlertRules | None:
        rule = await self.get_rule(rule_id)
        if rule is None:
            return None
        for k, v in fields.items():
            if v is not None and hasattr(rule, k):
                setattr(rule, k, v)
        await self.session.commit()
        await self.session.refresh(rule)
        return rule

    async def delete_rule(self, rule_id: UUID) -> bool:
        rule = await self.get_rule(rule_id)
        if rule is None:
            return False
        await self.session.delete(rule)
        await self.session.commit()
        return True
