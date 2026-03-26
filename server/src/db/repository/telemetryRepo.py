from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Agent, ResourceSnapshots, TelemetryEvents
from ...schemas import TelemetryIngestRequest


@dataclass(slots=True)
class TelemetryWriteResult:
    event: TelemetryEvents
    resource_snapshot: ResourceSnapshots | None


class TelemetryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def ingest(self, *, agent: Agent, payload: TelemetryIngestRequest) -> TelemetryWriteResult:
        event = TelemetryEvents(
            agent_id=agent.id,
            event_type="telemetry_batch",
            payload_json=payload.model_dump(mode="json"),
        )
        self.session.add(event)

        resource_snapshot = None
        if payload.resources is not None:
            resource_snapshot = ResourceSnapshots(
                agent_id=agent.id,
                cpu_pct=payload.resources.cpu_percent,
                mem_mb=payload.resources.memory_mb,
                mem_limit_mb=payload.resources.memory_limit_mb,
                net_bytes_sent=payload.resources.net_bytes_sent,
                net_bytes_recv=payload.resources.net_bytes_recv,
                disk_read_bytes=payload.resources.disk_read_bytes,
                disk_write_bytes=payload.resources.disk_write_bytes,
                timestamp=payload.timestamp,
            )
            self.session.add(resource_snapshot)

        await self.session.commit()
        await self.session.refresh(event)
        if resource_snapshot is not None:
            await self.session.refresh(resource_snapshot)

        return TelemetryWriteResult(
            event=event,
            resource_snapshot=resource_snapshot,
        )
