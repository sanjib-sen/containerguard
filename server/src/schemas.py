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


# ── Alert Rules ─────────────────────────────────────────────────────

class AlertRuleCreateRequest(BaseModel):
    name: str
    description: str | None = None
    metric: str = Field(description="One of: cpu_pct, mem_mb, mem_pct, net_bytes_sent, net_bytes_recv, disk_read_bytes, disk_write_bytes")
    operator: str = Field(description="One of: gt, ge, lt, le, eq")
    threshold: float
    severity: str = Field(description="One of: low, medium, high, critical")
    cooldown_sec: int = 300
    enabled: bool = True


class AlertRuleUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    metric: str | None = None
    operator: str | None = None
    threshold: float | None = None
    severity: str | None = None
    cooldown_sec: int | None = None
    enabled: bool | None = None


class AlertRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    metric: str
    operator: str
    threshold: float
    severity: str
    cooldown_sec: int
    enabled: bool


# ── Alerts ──────────────────────────────────────────────────────────

class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_id: UUID
    rule_id: UUID | None
    rule_name: str
    severity: str
    message: str
    status: str
    alert_metadata: dict[str, Any] | None
    created_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None


class AlertActionRequest(BaseModel):
    status: str = Field(description="One of: acknowledged, resolved, open")


# ── Compliance ──────────────────────────────────────────────────────

class ComplianceRuleCreateRequest(BaseModel):
    name: str
    description: str
    severity: str = Field(description="One of: low, medium, high, critical")
    rule_json: dict[str, Any] = Field(
        description="Predicate JSON. Supported types: 'no_root_processes', 'no_unauthorized_ports', 'no_sensitive_paths', 'network_blocklist', 'network_allowlist'"
    )
    enabled: bool = True


class ComplianceRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str
    rule_json: dict[str, Any]
    severity: str
    enabled: bool


class ComplianceResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_id: UUID
    rule_id: UUID
    status: str
    details: dict[str, Any] | None
    evaluated_at: datetime


# ── Scans ───────────────────────────────────────────────────────────

class ScanRequest(BaseModel):
    image: str = Field(description="Image to scan, e.g. 'python:3.12-slim' or 'redis:7'")
    agent_id: UUID | None = None


class ScanResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    image_name: str
    image_tag: str | None
    status: str
    vulnerabilities_json: dict[str, Any] | list[Any] | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    scanned_at: datetime
    agent_id: UUID | None
