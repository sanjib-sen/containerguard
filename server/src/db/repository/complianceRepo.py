from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ComplianceResults, ComplianceRules


class ComplianceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ── Rules ──────────────────────────────────────────────────

    async def list_rules(self, *, enabled_only: bool = False) -> list[ComplianceRules]:
        statement = select(ComplianceRules)
        if enabled_only:
            statement = statement.where(ComplianceRules.enabled == True)  # noqa: E712
        result = await self.session.scalars(statement)
        return list(result)

    async def get_rule(self, rule_id: UUID) -> ComplianceRules | None:
        return await self.session.get(ComplianceRules, rule_id)

    async def create_rule(
        self,
        *,
        name: str,
        description: str,
        rule_json: dict[str, Any],
        severity: str,
        enabled: bool = True,
    ) -> ComplianceRules:
        rule = ComplianceRules(
            name=name,
            description=description,
            rule_json=rule_json,
            severity=severity,
            enabled=enabled,
        )
        self.session.add(rule)
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

    # ── Results ────────────────────────────────────────────────

    async def record_result(
        self,
        *,
        agent_id: UUID,
        rule_id: UUID,
        status: str,
        details: dict[str, Any] | None = None,
    ) -> ComplianceResults:
        result = ComplianceResults(
            agent_id=agent_id,
            rule_id=rule_id,
            status=status,
            details=details,
            evaluated_at=datetime.now(timezone.utc),
        )
        self.session.add(result)
        await self.session.commit()
        await self.session.refresh(result)
        return result

    async def list_results(
        self,
        *,
        agent_id: UUID | None = None,
        limit: int = 200,
    ) -> list[ComplianceResults]:
        statement = select(ComplianceResults)
        if agent_id is not None:
            statement = statement.where(ComplianceResults.agent_id == agent_id)
        statement = statement.order_by(ComplianceResults.evaluated_at.desc()).limit(limit)
        result = await self.session.scalars(statement)
        return list(result)

    async def latest_per_agent_per_rule(self) -> list[ComplianceResults]:
        """Return the most recent compliance result for each (agent_id, rule_id) pair."""
        statement = select(ComplianceResults).order_by(ComplianceResults.evaluated_at.desc())
        result = await self.session.scalars(statement)
        seen: set[tuple[UUID, UUID]] = set()
        latest: list[ComplianceResults] = []
        for r in result:
            key = (r.agent_id, r.rule_id)
            if key in seen:
                continue
            seen.add(key)
            latest.append(r)
        return latest
