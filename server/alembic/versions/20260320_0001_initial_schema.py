"""Initial schema.

Revision ID: 20260320_0001
Revises:
Create Date: 2026-03-20 09:05:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260320_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("container_id", sa.Text(), nullable=False),
        sa.Column("hostname", sa.Text(), nullable=False),
        sa.Column("image", sa.Text(), nullable=False),
        sa.Column("ip", postgresql.INET(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_heartbeat", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("container_id"),
    )
    op.create_index("ix_agents_last_heartbeat", "agents", ["last_heartbeat"], unique=False)
    op.create_index("ix_agents_status", "agents", ["status"], unique=False)

    op.create_table(
        "telemetry_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_telemetry_events_agent_id", "telemetry_events", ["agent_id"], unique=False)
    op.create_index("ix_telemetry_events_created_at", "telemetry_events", ["created_at"], unique=False)

    op.create_table(
        "network_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("direction", sa.Text(), nullable=False),
        sa.Column("src_ip", postgresql.INET(), nullable=False),
        sa.Column("dst_ip", postgresql.INET(), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("protocol", sa.Text(), nullable=False),
        sa.Column("bytes", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_network_events_agent_id", "network_events", ["agent_id"], unique=False)
    op.create_index("ix_network_events_timestamp", "network_events", ["timestamp"], unique=False)

    op.create_table(
        "filesystem_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("pid", sa.Integer(), nullable=False),
        sa.Column("process_name", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_filesystem_events_agent_id", "filesystem_events", ["agent_id"], unique=False)
    op.create_index("ix_filesystem_events_timestamp", "filesystem_events", ["timestamp"], unique=False)

    op.create_table(
        "resource_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cpu_pct", sa.Float(), nullable=False),
        sa.Column("mem_mb", sa.Float(), nullable=False),
        sa.Column("mem_limit_mb", sa.Float(), nullable=False),
        sa.Column("net_bytes_sent", sa.Float(), nullable=False),
        sa.Column("net_bytes_recv", sa.Float(), nullable=False),
        sa.Column("disk_read_bytes", sa.Float(), nullable=False),
        sa.Column("disk_write_bytes", sa.Float(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_resource_snapshots_agent_id", "resource_snapshots", ["agent_id"], unique=False)
    op.create_index("ix_resource_snapshots_timestamp", "resource_snapshots", ["timestamp"], unique=False)

    op.create_table(
        "scan_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("image_name", sa.Text(), nullable=False),
        sa.Column("image_tag", sa.Text(), nullable=True),
        sa.Column("vulnerabilities_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("scanned_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scan_results_id", "scan_results", ["id"], unique=False)
    op.create_index("ix_scan_results_scanned_at", "scan_results", ["scanned_at"], unique=False)

    op.create_table(
        "compliance_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("rule_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "compliance_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_compliance_results_agent_id", "compliance_results", ["agent_id"], unique=False)
    op.create_index("ix_compliance_results_evaluated_at", "compliance_results", ["evaluated_at"], unique=False)

    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_name", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alerts_agent_id", "alerts", ["agent_id"], unique=False)
    op.create_index("ix_alerts_created_at", "alerts", ["created_at"], unique=False)

    op.create_table(
        "alert_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("metric", sa.Text(), nullable=False),
        sa.Column("operator", sa.Text(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("cooldown_sec", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("alert_rules")

    op.drop_index("ix_alerts_created_at", table_name="alerts")
    op.drop_index("ix_alerts_agent_id", table_name="alerts")
    op.drop_table("alerts")

    op.drop_index("ix_compliance_results_evaluated_at", table_name="compliance_results")
    op.drop_index("ix_compliance_results_agent_id", table_name="compliance_results")
    op.drop_table("compliance_results")

    op.drop_table("compliance_rules")

    op.drop_index("ix_scan_results_scanned_at", table_name="scan_results")
    op.drop_index("ix_scan_results_id", table_name="scan_results")
    op.drop_table("scan_results")

    op.drop_index("ix_resource_snapshots_timestamp", table_name="resource_snapshots")
    op.drop_index("ix_resource_snapshots_agent_id", table_name="resource_snapshots")
    op.drop_table("resource_snapshots")

    op.drop_index("ix_filesystem_events_timestamp", table_name="filesystem_events")
    op.drop_index("ix_filesystem_events_agent_id", table_name="filesystem_events")
    op.drop_table("filesystem_events")

    op.drop_index("ix_network_events_timestamp", table_name="network_events")
    op.drop_index("ix_network_events_agent_id", table_name="network_events")
    op.drop_table("network_events")

    op.drop_index("ix_telemetry_events_created_at", table_name="telemetry_events")
    op.drop_index("ix_telemetry_events_agent_id", table_name="telemetry_events")
    op.drop_table("telemetry_events")

    op.drop_index("ix_agents_status", table_name="agents")
    op.drop_index("ix_agents_last_heartbeat", table_name="agents")
    op.drop_table("agents")
