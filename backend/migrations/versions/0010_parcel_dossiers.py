"""Parcel questionnaires and durable analysis-to-report scheduling."""

from alembic import op

revision = "0010_parcel_dossiers"
down_revision = "0009_rag"
branch_labels = depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE parcel_profiles (
      video_id text NOT NULL,revision integer NOT NULL CHECK(revision>0),
      profile jsonb NOT NULL,actor text NOT NULL,created_at timestamptz NOT NULL DEFAULT now(),
      PRIMARY KEY(video_id,revision));
    CREATE TABLE parcel_dossiers (
      id uuid PRIMARY KEY,video_id text NOT NULL,profile_revision integer NOT NULL,
      analysis_id uuid NOT NULL REFERENCES console_tasks(id),
      task_id uuid UNIQUE REFERENCES document_tasks(id),actor text NOT NULL,
      status text NOT NULL DEFAULT 'waiting_analysis'
        CHECK(status IN ('waiting_analysis','queued','completed','error')),
      result jsonb,error text,created_at timestamptz NOT NULL DEFAULT now(),
      finished_at timestamptz,
      FOREIGN KEY(video_id,profile_revision) REFERENCES parcel_profiles(video_id,revision));
    CREATE INDEX parcel_dossiers_pending ON parcel_dossiers(status,created_at);
    CREATE INDEX parcel_dossiers_video ON parcel_dossiers(video_id,created_at DESC);
    """)


def downgrade() -> None:
    op.execute("""
    UPDATE document_tasks SET status='error',finished_at=now(),
      error='Dossiers désactivés par retour de migration'
      WHERE kind='rag' AND request->>'action'='parcel' AND status IN ('queued','running');
    DROP TABLE parcel_dossiers,parcel_profiles;
    """)
