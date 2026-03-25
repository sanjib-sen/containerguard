from __future__ import annotations

from datetime import datetime
from ipaddress import IPv4Address, IPv6Address
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


IPAddress = IPv4Address | IPv6Address


class AgentRegisterRequest(BaseModel):
    container_id: str
    hostname: str
    image: str
    ip: IPAddress | None = None


class AgentHeartbeatRequest(BaseModel):
    agent_id: UUID


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    container_id: str
    hostname: str
    image: str
    ip: IPAddress | None
    status: str
    registered_at: datetime
    last_heartbeat: datetime


class AgentHeartbeatResponse(BaseModel):
    agent_id: UUID
    status: str
    last_heartbeat: datetime


class NetworkConnectionPayload(BaseModel):
    direction: str
    src_ip: IPAddress
    dst_ip: IPAddress | None = None
    dst_port: int
    protocol: str
    bytes: int


class DNSQueryPayload(BaseModel):
    domain: str
    resolved_ip: IPAddress | None = None


class NetworkPayload(BaseModel):
    connections: list[NetworkConnectionPayload] = Field(default_factory=list)
    dns_queries: list[DNSQueryPayload] = Field(default_factory=list)


class PortPayload(BaseModel):
    port: int
    protocol: str
    pid: int
    process: str


class FilesystemEventPayload(BaseModel):
    type: str
    path: str
    pid: int
    process: str
    timestamp: datetime


class FilesystemPayload(BaseModel):
    events: list[FilesystemEventPayload] = Field(default_factory=list)


class ResourcesPayload(BaseModel):
    cpu_percent: float
    memory_mb: float
    memory_limit_mb: float
    net_bytes_sent: float
    net_bytes_recv: float
    disk_read_bytes: float
    disk_write_bytes: float


class ProcessPayload(BaseModel):
    pid: int
    command: str
    user: str
    started: datetime


class TelemetryIngestRequest(BaseModel):
    agent_id: UUID
    timestamp: datetime
    network: NetworkPayload | None = None
    ports: list[PortPayload] = Field(default_factory=list)
    filesystem: FilesystemPayload | None = None
    resources: ResourcesPayload | None = None
    processes: list[ProcessPayload] = Field(default_factory=list)


class TelemetryIngestResponse(BaseModel):
    event_id: UUID
    agent_id: UUID
    ingested_at: datetime
    resource_snapshot_id: UUID | None = None
    stored_resources: bool
    stored_network_connections: int
    stored_filesystem_events: int
    stored_processes: int
    stored_ports: int
    raw_payload: dict[str, Any]
