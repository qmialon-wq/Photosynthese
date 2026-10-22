"""Bibliothèque web, transferts fragmentés, tâches et registre de modèles."""

from alembic import op

revision = "0004_web_console"
down_revision = "0003_human_review"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE console_uploads (
      id uuid PRIMARY KEY, filename text NOT NULL, size bigint NOT NULL CHECK(size>0),
      status text NOT NULL DEFAULT 'uploading', actor text NOT NULL,
      created_at timestamptz NOT NULL DEFAULT now());
    CREATE TABLE console_chunks (
      upload_id uuid REFERENCES console_uploads(id), chunk_index integer NOT NULL,
      size integer NOT NULL, sha256 text NOT NULL, PRIMARY KEY(upload_id,chunk_index));
    CREATE TABLE console_videos (
      id text PRIMARY KEY, filename text NOT NULL, video_key text NOT NULL,
      sha256 text NOT NULL, species_candidate text, metadata jsonb NOT NULL,
      created_at timestamptz NOT NULL DEFAULT now());
    CREATE TABLE console_tasks (
      id uuid PRIMARY KEY, kind text NOT NULL, actor text NOT NULL,
      request jsonb NOT NULL, status text NOT NULL DEFAULT 'queued',
      progress jsonb NOT NULL DEFAULT '{}', result jsonb, error text,
      cancel_requested boolean NOT NULL DEFAULT false, published_at timestamptz,
      created_at timestamptz NOT NULL DEFAULT now(), finished_at timestamptz);
    CREATE INDEX console_task_outbox ON console_tasks(created_at)
      WHERE published_at IS NULL AND status='queued';
    CREATE TABLE console_logs (
      id bigserial PRIMARY KEY, task_id uuid NOT NULL REFERENCES console_tasks(id),
      message text NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
    CREATE INDEX console_logs_task ON console_logs(task_id,id);
    CREATE TABLE console_models (
      id uuid PRIMARY KEY, name text NOT NULL, checkpoint_key text NOT NULL,
      sha256 text NOT NULL UNIQUE, metadata jsonb NOT NULL, metrics jsonb NOT NULL,
      active boolean NOT NULL DEFAULT false, actor text NOT NULL,
      created_at timestamptz NOT NULL DEFAULT now());
    CREATE UNIQUE INDEX console_active_model ON console_models(active) WHERE active;
    """)


def downgrade() -> None:
    op.execute("""DROP TABLE console_models,console_logs,console_tasks,
      console_videos,console_chunks,console_uploads""")
