"""Revisioned point locations and immutable territorial consultations."""

from alembic import op

revision = "0013_territorial_context"
down_revision = "0012_authentication"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE parcel_locations (
        corpus_id uuid NOT NULL REFERENCES parcel_corpora(id),
        revision integer NOT NULL CHECK (revision > 0),
        latitude double precision NOT NULL CHECK (latitude BETWEEN -90 AND 90),
        longitude double precision NOT NULL CHECK (longitude BETWEEN -180 AND 180),
        provenance text NOT NULL CHECK (provenance IN ('numeric','map')),
        actor text NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY(corpus_id,revision)
    );
    CREATE TABLE territorial_queries (
        id uuid PRIMARY KEY,
        corpus_id uuid NOT NULL REFERENCES parcel_corpora(id),
        revision integer NOT NULL CHECK (revision > 0),
        input_sha256 text NOT NULL,
        inputs jsonb NOT NULL,
        layers jsonb NOT NULL DEFAULT '{}',
        result jsonb,
        task_id uuid REFERENCES document_tasks(id),
        actor text NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now(),
        finished_at timestamptz,
        UNIQUE(corpus_id,revision)
    );
    CREATE INDEX territorial_queries_latest ON territorial_queries(corpus_id,revision DESC);
    ALTER TABLE document_tasks DROP CONSTRAINT document_tasks_kind_check;
    ALTER TABLE document_tasks ADD CONSTRAINT document_tasks_kind_check
        CHECK (kind IN ('search','import','fetch','index','translate','rag',
                         'territorial','territorial_evidence'));
    """)


def downgrade() -> None:
    # Refuse silent loss of historical public evidence or user-entered locations.
    op.execute("""DO $$ BEGIN
      IF EXISTS(SELECT 1 FROM territorial_queries) OR EXISTS(SELECT 1 FROM parcel_locations) THEN
        RAISE EXCEPTION 'Exporter les analyses et localisations avant ce retour';
      END IF;
    END $$;
    DROP TABLE territorial_queries;
    DROP TABLE parcel_locations;
    """)
