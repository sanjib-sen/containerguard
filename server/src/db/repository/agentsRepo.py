from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Agent


@dataclass(slots=True)
class AgentStatusSyncResult:
    marked_unreachable: int
    marked_offline: int
    total_agents: int
    online_agents: int


class AgentsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_container_id(self, container_id: str) -> Agent | None:
        statement = select(Agent).where(Agent.container_id == container_id)
        return await self.session.scalar(statement)

    async def get_by_id(self, agent_id: UUID) -> Agent | None:
        return await self.session.get(Agent, agent_id)

    async def count_all(self) -> int:
        statement = select(func.count()).select_from(Agent)
        result = await self.session.scalar(statement)
        return int(result or 0)

    async def count_by_status(self, status: str) -> int:
        statement = select(func.count()).select_from(Agent).where(Agent.status == status)
        result = await self.session.scalar(statement)
        return int(result or 0)
    
    async def list_online_agents(self) -> list[UUID]:
        statement = select(Agent.id).where(Agent.status == "online")
        result = await self.session.scalars(statement)
        return list(result)

    async def sync_statuses(self, *, unreachable_after: timedelta, offline_after: timedelta) -> AgentStatusSyncResult:
        now = datetime.now(timezone.utc)
        unreachable_cutoff = now - unreachable_after
        offline_cutoff = now - offline_after
        
        offline_statement = (
            update(Agent)
            .where(
                Agent.status.in_(("online", "unreachable")),
                Agent.last_heartbeat < offline_cutoff,
            )
            .values(status="offline")
        )
        offline_result = await self.session.execute(offline_statement)

        unreachable_statement = (
            update(Agent)
            .where(
                Agent.status == "online",
                Agent.last_heartbeat < unreachable_cutoff,
            )
            .values(status="unreachable")
        )
        unreachable_result = await self.session.execute(unreachable_statement)

        await self.session.commit()

        total_agents = await self.count_all()
        online_agents = await self.count_by_status("online")

        return AgentStatusSyncResult(
            marked_unreachable=int(unreachable_result.rowcount or 0),
            marked_offline=int(offline_result.rowcount or 0),
            total_agents=total_agents,
            online_agents=online_agents,
        )

    async def register_agent(self, *, container_id: str, hostname: str, image: str, ip: str | None) -> Agent:
        now = datetime.now(timezone.utc)
        agent = await self.get_by_container_id(container_id)

        if agent is None:
            agent = Agent(
                container_id=container_id,
                hostname=hostname,
                image=image,
                ip=ip,
                status="online",
                registered_at=now,
                last_heartbeat=now,
            )
            self.session.add(agent)
        else:
            agent.hostname = hostname
            agent.image = image
            agent.ip = ip
            agent.status = "online"
            agent.last_heartbeat = now

        await self.session.commit()
        await self.session.refresh(agent)
        return agent

    async def record_heartbeat(self, *, agent_id: UUID) -> Agent | None:
        agent = await self.get_by_id(agent_id)
        if agent is None:
            return None

        agent.status = "online"
        agent.last_heartbeat = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(agent)
        return agent
