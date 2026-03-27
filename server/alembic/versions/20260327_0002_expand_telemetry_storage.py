"""Expand telemetry storage.

Revision ID: 20260327_0002
Revises: 20260320_0001
Create Date: 2026-03-27 10:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260327_0002"
down_revision: str | None = "20260320_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("network_events", "dst_ip", existing_type=postgresql.INET(), nullable=True)

    op.create_table(
        "port_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("protocol", sa.Text(), nullable=False),
        sa.Column("pid", sa.Integer(), nullable=False),
        sa.Column("process_name", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_port_snapshots_agent_id", "port_snapshots", ["agent_id"], unique=False)
    op.create_index("ix_port_snapshots_timestamp", "port_snapshots", ["timestamp"], unique=False)

    op.create_table(
        "process_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pid", sa.Integer(), nullable=False),
        sa.Column("command", sa.Text(), nullable=False),
        sa.Column("user", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_process_snapshots_agent_id", "process_snapshots", ["agent_id"], unique=False)
    op.create_index("ix_process_snapshots_timestamp", "process_snapshots", ["timestamp"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_process_snapshots_timestamp", table_name="process_snapshots")
    op.drop_index("ix_process_snapshots_agent_id", table_name="process_snapshots")
    op.drop_table("process_snapshots")

    op.drop_index("ix_port_snapshots_timestamp", table_name="port_snapshots")
    op.drop_index("ix_port_snapshots_agent_id", table_name="port_snapshots")
    op.drop_table("port_snapshots")

    op.alter_column("network_events", "dst_ip", existing_type=postgresql.INET(), nullable=False)
