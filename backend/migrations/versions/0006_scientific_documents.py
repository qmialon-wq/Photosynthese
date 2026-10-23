"""Veille scientifique, provenance, fichiers, texte et file indépendante."""

from alembic import op

revision = "0006_scientific_documents"
down_revision = "0005_classifier_registry"
branch_labels = depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE document_watches (
      id uuid PRIMARY KEY,name text NOT NULL UNIQUE,definition jsonb NOT NULL,
      interval_seconds integer NOT NULL CHECK(interval_seconds>=60),enabled boolean NOT NULL,
      next_run timestamptz NOT NULL DEFAULT now(),actor text NOT NULL,
      created_at timestamptz NOT NULL DEFAULT now());
    CREATE TABLE document_tasks (
      id uuid PRIMARY KEY,kind text NOT NULL CHECK(kind IN ('search','import','fetch','index')),
      request jsonb NOT NULL,actor text NOT NULL,status text NOT NULL DEFAULT 'queued'
        CHECK(status IN ('queued','running','completed','partial','error')),
      dedup_key text UNIQUE,published_at timestamptz,attempts integer NOT NULL DEFAULT 0,
      result jsonb,error text,created_at timestamptz NOT NULL DEFAULT now(),
      started_at timestamptz,finished_at timestamptz);
    CREATE TABLE scientific_documents (
      id uuid PRIMARY KEY,doi text UNIQUE,title text NOT NULL,authors jsonb NOT NULL DEFAULT '[]',
      published_date text,abstract text,url text,license text,language text,
      identifiers jsonb NOT NULL DEFAULT '{}',metadata jsonb NOT NULL DEFAULT '{}',
      processing_status text NOT NULL DEFAULT 'discovered'
        CHECK(processing_status IN ('discovered','imported','indexed','inaccessible')),
      relevance text NOT NULL DEFAULT 'pending'
        CHECK(relevance IN ('pending','accepted','rejected')),
      quality text NOT NULL DEFAULT 'pending' CHECK(quality IN ('pending','accepted','rejected')),
      status text GENERATED ALWAYS AS
        (CASE WHEN relevance='rejected' OR quality='rejected' THEN 'rejected'
          ELSE processing_status END) STORED,
      merged_into uuid REFERENCES scientific_documents(id),
      created_at timestamptz NOT NULL DEFAULT now(),updated_at timestamptz NOT NULL DEFAULT now());
    CREATE TABLE document_identifiers (
      namespace text NOT NULL,value text NOT NULL,document_id uuid NOT NULL
        REFERENCES scientific_documents(id),PRIMARY KEY(namespace,value));
    CREATE TABLE document_provenance (
      id bigserial PRIMARY KEY,document_id uuid NOT NULL REFERENCES scientific_documents(id),
      source text NOT NULL,source_id text NOT NULL,snapshot_sha256 text NOT NULL,raw jsonb NOT NULL,
      task_id uuid REFERENCES document_tasks(id),observed_at timestamptz NOT NULL DEFAULT now(),
      UNIQUE(source,source_id,snapshot_sha256));
    CREATE TABLE document_watch_matches (
      watch_id uuid REFERENCES document_watches(id),
      document_id uuid REFERENCES scientific_documents(id),
      PRIMARY KEY(watch_id,document_id));
    CREATE TABLE document_assets (
      id uuid PRIMARY KEY,document_id uuid NOT NULL REFERENCES scientific_documents(id),
      sha256 text NOT NULL UNIQUE,storage_key text NOT NULL,format text NOT NULL,
      source_url text,license text NOT NULL,rights_evidence jsonb NOT NULL,
      byte_size bigint NOT NULL,
      extraction_version text,extraction_warnings jsonb NOT NULL DEFAULT '[]',
      created_at timestamptz NOT NULL DEFAULT now());
    CREATE TABLE document_pages (
      asset_id uuid REFERENCES document_assets(id),page_number integer NOT NULL,
      raw_text text NOT NULL,clean_text text NOT NULL,language text NOT NULL,
      references_data jsonb NOT NULL DEFAULT '[]',
      PRIMARY KEY(asset_id,page_number));
    CREATE TABLE document_chunks (
      id text PRIMARY KEY,asset_id uuid REFERENCES document_assets(id),page_number integer NOT NULL,
      ordinal integer NOT NULL,start_char integer NOT NULL,end_char integer NOT NULL,
      text text NOT NULL,language text NOT NULL,is_reference boolean NOT NULL,
      search_vector tsvector GENERATED ALWAYS AS (to_tsvector('simple',text)) STORED,
      FOREIGN KEY(asset_id,page_number) REFERENCES document_pages(asset_id,page_number),
      UNIQUE(asset_id,page_number,ordinal));
    CREATE INDEX document_chunks_search ON document_chunks USING gin(search_vector);
    CREATE TABLE document_reviews (
      id bigserial PRIMARY KEY,document_id uuid REFERENCES scientific_documents(id),
      relevance text NOT NULL,quality text NOT NULL,note text NOT NULL,actor text NOT NULL,
      created_at timestamptz NOT NULL DEFAULT now());
    CREATE TABLE document_events (
      id bigserial PRIMARY KEY,task_id uuid REFERENCES document_tasks(id),
      document_id uuid REFERENCES scientific_documents(id),stage text NOT NULL,
      level text NOT NULL,message text NOT NULL,data jsonb NOT NULL DEFAULT '{}',
      created_at timestamptz NOT NULL DEFAULT now());
    CREATE INDEX document_tasks_pending ON document_tasks(status,created_at);
    CREATE INDEX document_events_task ON document_events(task_id,id);
    CREATE INDEX document_assets_document ON document_assets(document_id);
    """)


def downgrade() -> None:
    op.execute("""DROP TABLE document_events,document_reviews,document_chunks,document_pages,
      document_assets,document_watch_matches,document_provenance,document_identifiers,
      scientific_documents,document_tasks,document_watches;""")
