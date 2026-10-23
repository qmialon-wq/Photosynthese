"""Versioned local embeddings and auditable extractive reports."""

from alembic import op

revision = "0009_rag"
down_revision = "0008_document_collection"
branch_labels = depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE rag_embedding_versions (
      id text PRIMARY KEY, manifest jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
    CREATE TABLE rag_embeddings (
      chunk_id text REFERENCES document_chunks(id) ON DELETE CASCADE,
      version text REFERENCES rag_embedding_versions(id), text_sha256 text NOT NULL,
      embedding vector NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
      PRIMARY KEY(chunk_id,version));
    CREATE INDEX rag_embeddings_version ON rag_embeddings(version);
    CREATE TABLE rag_runs (
      id uuid PRIMARY KEY, task_id uuid UNIQUE REFERENCES document_tasks(id), kind text NOT NULL,
      request jsonb NOT NULL, result jsonb NOT NULL, actor text NOT NULL,
      created_at timestamptz NOT NULL DEFAULT now());
    CREATE TABLE rag_video_context (
      video_id text PRIMARY KEY REFERENCES review_videos(id),
      context jsonb NOT NULL, actor text NOT NULL, updated_at timestamptz NOT NULL DEFAULT now());
    CREATE TABLE rag_context_history (
      id bigserial PRIMARY KEY, video_id text NOT NULL REFERENCES review_videos(id),
      context jsonb NOT NULL, actor text NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
    CREATE TABLE rag_taxonomy (
      species text PRIMARY KEY REFERENCES document_species_catalog(name),
      cd_nom bigint NOT NULL CHECK(cd_nom>0), taxref_version text NOT NULL,
      scientific_name text NOT NULL, source_url text NOT NULL, actor text NOT NULL,
      updated_at timestamptz NOT NULL DEFAULT now());
    CREATE TABLE rag_document_context (
      document_id uuid PRIMARY KEY REFERENCES scientific_documents(id),
      context jsonb NOT NULL, actor text NOT NULL, updated_at timestamptz NOT NULL DEFAULT now());
    ALTER TABLE document_tasks DROP CONSTRAINT document_tasks_kind_check;
    ALTER TABLE document_tasks ADD CONSTRAINT document_tasks_kind_check
      CHECK(kind IN ('search','import','fetch','index','translate','rag'));
    """)


def downgrade() -> None:
    op.execute("""
    DROP TABLE rag_document_context,rag_taxonomy,rag_context_history,rag_video_context,rag_runs,
      rag_embeddings,rag_embedding_versions;
    ALTER TABLE document_tasks DROP CONSTRAINT document_tasks_kind_check;
    UPDATE document_tasks SET kind='index',status='error',finished_at=now(),
      request=request || '{"rolled_back_kind":"rag"}'::jsonb,
      error='RAG désactivé par retour de migration' WHERE kind='rag';
    ALTER TABLE document_tasks ADD CONSTRAINT document_tasks_kind_check
      CHECK(kind IN ('search','import','fetch','index','translate'));
    """)
