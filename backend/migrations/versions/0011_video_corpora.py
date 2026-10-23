"""A parcel dossier can aggregate a deduplicated video corpus."""

from alembic import op

revision = "0011_video_corpora"
down_revision = "0010_parcel_dossiers"
branch_labels = depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE parcel_corpora (
      id uuid PRIMARY KEY,actor text NOT NULL,created_at timestamptz NOT NULL DEFAULT now());
    CREATE TABLE parcel_corpus_videos (
      corpus_id uuid REFERENCES parcel_corpora(id),video_id text NOT NULL,
      sha256 text NOT NULL,filename text NOT NULL,ordinal integer NOT NULL,
      PRIMARY KEY(corpus_id,video_id),UNIQUE(corpus_id,sha256));
    CREATE TABLE parcel_corpus_profiles (
      corpus_id uuid REFERENCES parcel_corpora(id),revision integer NOT NULL CHECK(revision>0),
      profile jsonb NOT NULL,actor text NOT NULL,created_at timestamptz NOT NULL DEFAULT now(),
      PRIMARY KEY(corpus_id,revision));
    ALTER TABLE parcel_dossiers ALTER COLUMN video_id DROP NOT NULL;
    ALTER TABLE parcel_dossiers ADD COLUMN corpus_id uuid REFERENCES parcel_corpora(id);
    ALTER TABLE parcel_dossiers ADD FOREIGN KEY(corpus_id,profile_revision)
      REFERENCES parcel_corpus_profiles(corpus_id,revision);
    ALTER TABLE parcel_dossiers ADD CHECK ((video_id IS NULL) <> (corpus_id IS NULL));
    CREATE INDEX parcel_dossiers_corpus ON parcel_dossiers(corpus_id,created_at DESC);
    CREATE TABLE parcel_dossier_videos (
      dossier_id uuid REFERENCES parcel_dossiers(id),video_id text NOT NULL,
      sha256 text NOT NULL,filename text NOT NULL,ordinal integer NOT NULL,
      analysis_id uuid NOT NULL REFERENCES console_tasks(id),
      PRIMARY KEY(dossier_id,video_id),UNIQUE(dossier_id,sha256));
    """)


def downgrade() -> None:
    # Historical multi-video snapshots must not silently become single-video reports.
    op.execute("""DO $$ BEGIN
      IF EXISTS(SELECT 1 FROM parcel_corpora) THEN
        RAISE EXCEPTION 'Exporter et archiver les dossiers multi-videos avant ce retour';
      END IF;
    END $$;
    DROP TABLE parcel_dossier_videos;
    ALTER TABLE parcel_dossiers DROP COLUMN corpus_id;
    ALTER TABLE parcel_dossiers ALTER COLUMN video_id SET NOT NULL;
    DROP TABLE parcel_corpus_profiles,parcel_corpus_videos,parcel_corpora;
    """)
