from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import (
    Agent,
    FilesystemEvents,
    NetworkEvents,
    PortSnapshots,
    ProcessSnapshots,
    ResourceSnapshots,
    TelemetryEvents,
)
from ...schemas import TelemetryIngestRequest


@dataclass(slots=True)
class TelemetryWriteResult:
    event: TelemetryEvents
    resource_snapshot: ResourceSnapshots | None
    stored_network_connections: int
    stored_filesystem_events: int
    stored_processes: int
    stored_ports: int


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

        stored_network_connections = 0
        if payload.network is not None:
            network_events = [
                NetworkEvents(
                    agent_id=agent.id,
                    direction=connection.direction,
                    src_ip=str(connection.src_ip),
                    dst_ip=str(connection.dst_ip) if connection.dst_ip is not None else None,
                    port=connection.dst_port,
                    protocol=connection.protocol,
                    bytes=connection.bytes,
                    timestamp=payload.timestamp,
                )
                for connection in payload.network.connections
            ]
            self.session.add_all(network_events)
            stored_network_connections = len(network_events)

        stored_filesystem_events = 0
        if payload.filesystem is not None:
            filesystem_events = [
                FilesystemEvents(
                    agent_id=agent.id,
                    event_type=event_payload.type,
                    path=event_payload.path,
                    pid=event_payload.pid,
                    process_name=event_payload.process,
                    timestamp=event_payload.timestamp,
                )
                for event_payload in payload.filesystem.events
            ]
            self.session.add_all(filesystem_events)
            stored_filesystem_events = len(filesystem_events)

        port_snapshots = [
            PortSnapshots(
                agent_id=agent.id,
                port=port.port,
                protocol=port.protocol,
                pid=port.pid,
                process_name=port.process,
                timestamp=payload.timestamp,
            )
            for port in payload.ports
        ]
        self.session.add_all(port_snapshots)

        process_snapshots = [
            ProcessSnapshots(
                agent_id=agent.id,
                pid=process.pid,
                command=process.command,
                user=process.user,
                started_at=process.started,
                timestamp=payload.timestamp,
            )
            for process in payload.processes
        ]
        self.session.add_all(process_snapshots)

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
            stored_network_connections=stored_network_connections,
            stored_filesystem_events=stored_filesystem_events,
            stored_processes=len(process_snapshots),
            stored_ports=len(port_snapshots),
        )
