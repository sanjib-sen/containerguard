from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, Text, func, text
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Agent(Base):
    """
    agent table current record for each monitored container.
    """
    __tablename__ = "agents"
    __table_args__ = (
        Index("ix_agents_status", "status"),
        Index("ix_agents_last_heartbeat", "last_heartbeat"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    container_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    hostname: Mapped[str] = mapped_column(Text, nullable=False)
    image: Mapped[str] = mapped_column(Text, nullable=False)
    ip: Mapped[str | None] = mapped_column(INET, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    last_heartbeat: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

class TelemetryEvents(Base):
    """
    telemetry events table partitioned by time
    """
    __tablename__ = "telemetry_events"
    __table_args__ = (
        Index("ix_telemetry_events_agent_id", "agent_id"),
        Index("ix_telemetry_events_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[Any] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

class NetworkEvents(Base):
    """
    network events table
    """
    __tablename__ = "network_events"
    __table_args__ = (
        Index("ix_network_events_agent_id", "agent_id"),
        Index("ix_network_events_timestamp", "timestamp"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    direction: Mapped[str] = mapped_column(Text, nullable=False)
    src_ip: Mapped[str] = mapped_column(INET, nullable=False)
    dst_ip: Mapped[str | None] = mapped_column(INET, nullable=True)
    port: Mapped[int] = mapped_column(nullable=False)
    protocol: Mapped[str] = mapped_column(Text, nullable=False)
    bytes: Mapped[int] = mapped_column(nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

class FilesystemEvents(Base):
    """
    filesystem events table
    """
    __tablename__ = "filesystem_events"
    __table_args__ = (
        Index("ix_filesystem_events_agent_id", "agent_id"),
        Index("ix_filesystem_events_timestamp", "timestamp"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    pid: Mapped[int] = mapped_column(nullable=False)
    process_name: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class PortSnapshots(Base):
    """
    port snapshots table
    """
    __tablename__ = "port_snapshots"
    __table_args__ = (
        Index("ix_port_snapshots_agent_id", "agent_id"),
        Index("ix_port_snapshots_timestamp", "timestamp"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    port: Mapped[int] = mapped_column(nullable=False)
    protocol: Mapped[str] = mapped_column(Text, nullable=False)
    pid: Mapped[int] = mapped_column(nullable=False)
    process_name: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ProcessSnapshots(Base):
    """
    process snapshots table
    """
    __tablename__ = "process_snapshots"
    __table_args__ = (
        Index("ix_process_snapshots_agent_id", "agent_id"),
        Index("ix_process_snapshots_timestamp", "timestamp"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    pid: Mapped[int] = mapped_column(nullable=False)
    command: Mapped[str] = mapped_column(Text, nullable=False)
    user: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ResourceSnapshots(Base):
    """
    resource snapshots table
    """
    __tablename__ = "resource_snapshots"
    __table_args__ = (
        Index("ix_resource_snapshots_agent_id", "agent_id"),
        Index("ix_resource_snapshots_timestamp", "timestamp"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    cpu_pct: Mapped[float] = mapped_column(nullable=False)
    mem_mb: Mapped[float] = mapped_column(nullable=False)
    mem_limit_mb: Mapped[float] = mapped_column(nullable=False)
    net_bytes_sent: Mapped[float] = mapped_column(nullable=False)
    net_bytes_recv: Mapped[float] = mapped_column(nullable=False)
    disk_read_bytes: Mapped[float] = mapped_column(nullable=False)
    disk_write_bytes: Mapped[float] = mapped_column(nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

class ScanResults(Base):
    """
    scan results table
    """
    __tablename__ = "scan_results"
    __table_args__ = (
        Index("ix_scan_results_id", "id"),
        Index("ix_scan_results_scanned_at", "scanned_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    image_name: Mapped[str] = mapped_column(Text, nullable=False)
    image_tag: Mapped[str | None] = mapped_column(Text, nullable=True)
    vulnerabilities_json: Mapped[Any] = mapped_column(JSONB, nullable=False)
    scanned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    status: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

class ComplianceRules(Base):
    """
    compliance rules table
    """
    __tablename__ = "compliance_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    rule_json: Mapped[Any] = mapped_column(JSONB, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))

class ComplianceResults(Base):
    """
    compliance results table
    """
    __tablename__ = "compliance_results"
    __table_args__ = (
        Index("ix_compliance_results_agent_id", "agent_id"),
        Index("ix_compliance_results_evaluated_at", "evaluated_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[Any] = mapped_column(JSONB, nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

class Alerts(Base):
    """
    alerts table
    """
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_agent_id", "agent_id"),
        Index("ix_alerts_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    rule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    rule_name: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    alert_metadata: Mapped[Any] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class AlertRules(Base):
    """
    alert rules table
    """
    __tablename__ = "alert_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metric: Mapped[str] = mapped_column(Text, nullable=False)
    operator: Mapped[str] = mapped_column(Text, nullable=False)
    threshold: Mapped[float] = mapped_column(nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    cooldown_sec: Mapped[int] = mapped_column(nullable=False)
    enabled: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))
