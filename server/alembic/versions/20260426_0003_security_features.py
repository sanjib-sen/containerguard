"""Security features: extend alert_rules, add alerts.metadata, add scan_results metadata.

Revision ID: 20260426_0003
Revises: 20260327_0002
Create Date: 2026-04-26 10:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260426_0003"
down_revision: str | None = "20260327_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Extend alert_rules with name and description
    op.add_column("alert_rules", sa.Column("name", sa.Text(), nullable=False, server_default="Unnamed Rule"))
    op.add_column("alert_rules", sa.Column("description", sa.Text(), nullable=True))
    # Drop the server default for new rows now that existing rows are populated
    op.alter_column("alert_rules", "name", server_default=None)

    # Extend alerts with metadata for context (the value that triggered, the rule_id, etc.)
    op.add_column("alerts", sa.Column("rule_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("alerts", sa.Column("alert_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # Add resolved_at to alerts for full lifecycle (open -> acknowledged -> resolved)
    op.add_column("alerts", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True))

    # Extend scan_results with started/completed timestamps and a target identifier
    op.add_column("scan_results", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("scan_results", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("scan_results", sa.Column("error_message", sa.Text(), nullable=True))
    op.add_column("scan_results", sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=True))


def downgrade() -> None:
    op.drop_column("scan_results", "agent_id")
    op.drop_column("scan_results", "error_message")
    op.drop_column("scan_results", "completed_at")
    op.drop_column("scan_results", "started_at")

    op.drop_column("alerts", "resolved_at")
    op.drop_column("alerts", "alert_metadata")
    op.drop_column("alerts", "rule_id")

    op.drop_column("alert_rules", "description")
    op.drop_column("alert_rules", "name")
