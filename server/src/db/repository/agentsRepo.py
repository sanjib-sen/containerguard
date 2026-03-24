from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Agent


class AgentsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_container_id(self, container_id: str) -> Agent | None:
        statement = select(Agent).where(Agent.container_id == container_id)
        return await self.session.scalar(statement)

    async def get_by_id(self, agent_id: UUID) -> Agent | None:
        return await self.session.get(Agent, agent_id)

    async def register_agent(
        self,
        *,
        container_id: str,
        hostname: str,
        image: str,
        ip: str | None,
    ) -> Agent:
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
