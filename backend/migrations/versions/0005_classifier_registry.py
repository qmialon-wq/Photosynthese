"""Familles, comparaisons et historique de promotion des classificateurs."""

from alembic import op

revision = "0005_classifier_registry"
down_revision = "0004_web_console"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    ALTER TABLE console_models
      ADD COLUMN family text NOT NULL DEFAULT 'existing'
        CHECK(family IN ('existing','supervised','embedding')),
      ADD COLUMN status text NOT NULL DEFAULT 'candidate'
        CHECK(status IN ('candidate','validated','active','archived')),
      ADD COLUMN version text,
      ADD COLUMN dataset_version text,
      ADD COLUMN preprocessing_version text NOT NULL DEFAULT 'legacy-imagenet-resize-v1';
    UPDATE console_models SET status=CASE WHEN active THEN 'active' ELSE 'candidate' END,
      version=sha256;
    ALTER TABLE console_models ADD CONSTRAINT model_active_status
      CHECK(active=(status='active'));
    CREATE TABLE classifier_comparisons (
      id uuid PRIMARY KEY, report jsonb NOT NULL, report_sha256 text NOT NULL,
      actor text NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
    CREATE TABLE model_promotions (
      id uuid PRIMARY KEY, model_id uuid NOT NULL REFERENCES console_models(id),
      previous_model_id uuid REFERENCES console_models(id),
      comparison_id uuid REFERENCES classifier_comparisons(id),
      action text NOT NULL CHECK(action IN ('bootstrap','promotion','rollback','rejected')),
      actor text NOT NULL, justification jsonb NOT NULL,
      created_at timestamptz NOT NULL DEFAULT now());
    INSERT INTO model_promotions(id,model_id,action,actor,justification)
      SELECT id,id,'bootstrap','migration','{"reason":"Champion actif préservé avant comparaison"}'
      FROM console_models WHERE active;
    """)


def downgrade() -> None:
    op.execute("""DROP TABLE model_promotions,classifier_comparisons;
      ALTER TABLE console_models DROP CONSTRAINT model_active_status,
      DROP COLUMN family,DROP COLUMN status,DROP COLUMN version,
      DROP COLUMN dataset_version,DROP COLUMN preprocessing_version;""")
