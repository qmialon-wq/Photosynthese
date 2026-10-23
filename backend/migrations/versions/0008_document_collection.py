"""Retrait du corpus par espèce et traductions dérivées des pages originales."""

from alembic import op

revision = "0008_document_collection"
down_revision = "0007_document_species"
branch_labels = depends_on = None


def upgrade() -> None:
    op.execute("""
    ALTER TABLE document_species ADD COLUMN excluded boolean NOT NULL DEFAULT false;
    UPDATE document_species SET excluded=true WHERE origin='human' AND NOT enabled;
    ALTER TABLE document_tasks DROP CONSTRAINT document_tasks_kind_check;
    ALTER TABLE document_tasks ADD CONSTRAINT document_tasks_kind_check
      CHECK(kind IN ('search','import','fetch','index','translate'));
    CREATE TABLE document_page_translations (
      asset_id uuid NOT NULL,page_number integer NOT NULL,
      source_text text NOT NULL,source_sha256 text NOT NULL,
      translated_text text NOT NULL,engine text NOT NULL,
      created_at timestamptz NOT NULL DEFAULT now(),PRIMARY KEY(asset_id,page_number),
      FOREIGN KEY(asset_id,page_number) REFERENCES document_pages(asset_id,page_number)
        ON DELETE CASCADE);
    """)


def downgrade() -> None:
    op.execute("""DROP TABLE document_page_translations;
    ALTER TABLE document_species DROP COLUMN excluded;
    ALTER TABLE document_tasks DROP CONSTRAINT document_tasks_kind_check;
    UPDATE document_tasks SET kind='index',status='error',
      request=request || '{"rolled_back_kind":"translate"}'::jsonb,
      error='Traduction désactivée par retour de migration',finished_at=now()
      WHERE kind='translate';
    ALTER TABLE document_tasks ADD CONSTRAINT document_tasks_kind_check
      CHECK(kind IN ('search','import','fetch','index'));""")
