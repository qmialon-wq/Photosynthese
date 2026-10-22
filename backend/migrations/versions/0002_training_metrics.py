"""Métriques d'entraînement avec identifiant de run et événements idempotents."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0002_training_metrics"
down_revision = "0001_enable_vector"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "training_runs",
        sa.Column("run_id", sa.String(80), primary_key=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("metadata", JSONB, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "training_metrics",
        sa.Column("run_id", sa.String(80), sa.ForeignKey("training_runs.run_id"), primary_key=True),
        sa.Column("event_key", sa.String(100), primary_key=True),
        sa.Column("metrics", JSONB, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("training_metrics")
    op.drop_table("training_runs")
