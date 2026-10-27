"""Accounts, revocable sessions and traceable erasure requests."""

from alembic import op

revision = "0012_authentication"
down_revision = "0011_video_corpora"
branch_labels = depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE app_users (
      id uuid PRIMARY KEY,email text,display_name text NOT NULL,password_hash text,
      role text NOT NULL CHECK(role IN ('client','admin')),
      created_at timestamptz NOT NULL DEFAULT now(),updated_at timestamptz NOT NULL DEFAULT now(),
      deleted_at timestamptz);
    CREATE UNIQUE INDEX app_users_email ON app_users(lower(email)) WHERE deleted_at IS NULL;
    CREATE TABLE auth_sessions (
      token_hash text PRIMARY KEY,user_id uuid NOT NULL REFERENCES app_users(id),
      created_at timestamptz NOT NULL DEFAULT now(),last_seen_at timestamptz NOT NULL DEFAULT now(),
      expires_at timestamptz NOT NULL);
    CREATE INDEX auth_sessions_user ON auth_sessions(user_id);
    CREATE TABLE auth_bootstrap (singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),
      token_hash text NOT NULL,consumed_at timestamptz);
    CREATE TABLE auth_password_resets (
      token_hash text PRIMARY KEY,user_id uuid NOT NULL REFERENCES app_users(id),
      expires_at timestamptz NOT NULL);
    CREATE TABLE auth_events (
      id bigserial PRIMARY KEY,actor uuid,target uuid,action text NOT NULL,
      created_at timestamptz NOT NULL DEFAULT now());
    CREATE TABLE auth_erasure_requests (
      id uuid PRIMARY KEY,user_id uuid NOT NULL REFERENCES app_users(id),
      status text NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','processing','completed')),
      note text NOT NULL DEFAULT '',requested_at timestamptz NOT NULL DEFAULT now(),
      reviewed_at timestamptz,reviewed_by uuid REFERENCES app_users(id));
    CREATE INDEX auth_erasure_pending ON auth_erasure_requests(status,requested_at);
    CREATE INDEX auth_owned_imports ON console_tasks(actor,(result->>'video_id'))
      WHERE kind IN ('import_upload','import_local');
    """)


def downgrade():
    op.execute("""DROP INDEX auth_owned_imports;
      DROP TABLE auth_erasure_requests,auth_events,auth_password_resets,
      auth_bootstrap,auth_sessions,app_users""")
