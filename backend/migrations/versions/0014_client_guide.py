"""Remember client guide discovery per account, independently of the browser."""

from alembic import op

revision = "0014_client_guide"
down_revision = "0013_territorial_context"
branch_labels = depends_on = None


def upgrade():
    op.execute("ALTER TABLE app_users ADD COLUMN client_guide_seen_at timestamptz")


def downgrade():
    op.execute("ALTER TABLE app_users DROP COLUMN client_guide_seen_at")
