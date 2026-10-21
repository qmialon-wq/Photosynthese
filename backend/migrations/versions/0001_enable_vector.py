"""Active pgvector, sans créer de tables métier anticipées."""

from alembic import op

revision = "0001_enable_vector"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    # Sans CASCADE : refuser la suppression si des objets dépendent de l'extension.
    op.execute("DROP EXTENSION IF EXISTS vector")
