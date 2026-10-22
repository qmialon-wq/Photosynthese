"""Revue humaine, sources immuables, outbox et snapshots de datasets."""

from alembic import op

revision = "0003_human_review"
down_revision = "0002_training_metrics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE review_species (
      name text PRIMARY KEY, class_index integer UNIQUE NOT NULL,
      manifest_version text NOT NULL DEFAULT 'v3-10.1');
    INSERT INTO review_species(name,class_index) VALUES
      ('chevreuil',0),('sanglier',1),('buse',2),('pigeons',3),('martres',4),
      ('renards',5),('blaireaux',6),('chouette',7),('geai',8),('faisans',9);
    CREATE TABLE review_groups (
      id text PRIMARY KEY, split text NOT NULL CHECK(split IN ('train','val','test')),
      test_locked boolean NOT NULL DEFAULT false, locked_at timestamptz);
    CREATE TABLE review_videos (
      id text PRIMARY KEY, group_id text NOT NULL REFERENCES review_groups(id),
      source_key text NOT NULL UNIQUE, original_name text NOT NULL,
      species_candidate text REFERENCES review_species(name), candidates jsonb NOT NULL,
      status text NOT NULL DEFAULT 'processing', diagnostics jsonb NOT NULL DEFAULT '{}',
      created_at timestamptz NOT NULL DEFAULT now());
    CREATE TABLE review_imports (
      id uuid PRIMARY KEY, video_id text NOT NULL REFERENCES review_videos(id),
      original_name text NOT NULL, actor text NOT NULL, provenance jsonb NOT NULL,
      created_at timestamptz NOT NULL DEFAULT now());
    CREATE TABLE review_frames (
      id text PRIMARY KEY, video_id text NOT NULL REFERENCES review_videos(id),
      frame_index integer NOT NULL, time_seconds double precision NOT NULL,
      image_key text NOT NULL, sha256 text NOT NULL, width integer NOT NULL, height integer
        NOT NULL,
      quality jsonb NOT NULL, UNIQUE(video_id,frame_index));
    CREATE INDEX review_frames_sha ON review_frames(sha256);
    CREATE TABLE review_similarities (
      first_id text NOT NULL REFERENCES review_frames(id),
      second_id text NOT NULL REFERENCES review_frames(id), reason text NOT NULL,
      PRIMARY KEY(first_id,second_id), CHECK(first_id < second_id));
    CREATE INDEX review_similarities_second ON review_similarities(second_id);
    CREATE TABLE review_samples (
      id text PRIMARY KEY, frame_id text NOT NULL REFERENCES review_frames(id),
      original_box jsonb NOT NULL, original_crop_key text NOT NULL,
      detector_identity text NOT NULL, detection_score double precision NOT NULL,
      predicted_label text REFERENCES review_species(name), classification_score double
        precision,
      probabilities jsonb, current_revision integer NOT NULL DEFAULT 0);
    CREATE TABLE review_revisions (
      sample_id text NOT NULL REFERENCES review_samples(id), revision integer NOT NULL,
      state text NOT NULL CHECK(state IN ('pending','validated','corrected','rejected')),
      label text REFERENCES review_species(name), box jsonb NOT NULL, recipe jsonb NOT NULL,
      crop_key text, crop_sha256 text, quality jsonb,
      render_status text NOT NULL CHECK(render_status IN ('pending','ready','error')),
      actor text NOT NULL, provenance jsonb NOT NULL, created_at timestamptz NOT NULL
        DEFAULT now(),
      PRIMARY KEY(sample_id,revision),
      CHECK((state IN ('validated','corrected') AND label IS NOT NULL)
         OR (state IN ('pending','rejected') AND label IS NULL)));
    ALTER TABLE review_samples ADD CONSTRAINT review_current_revision_fk
      FOREIGN KEY(id,current_revision) REFERENCES review_revisions(sample_id,revision)
      DEFERRABLE INITIALLY DEFERRED;
    CREATE TABLE review_operations (
      id uuid PRIMARY KEY, kind text NOT NULL CHECK(kind IN
        ('import_video','render_crop','export_dataset','rebuild_export')),
      payload jsonb NOT NULL, actor text NOT NULL, status text NOT NULL DEFAULT 'queued'
        CHECK(status IN ('queued','running','completed','error')),
      published_at timestamptz, result jsonb, error text,
      created_at timestamptz NOT NULL DEFAULT now(), finished_at timestamptz);
    CREATE INDEX review_outbox ON review_operations(created_at) WHERE published_at IS NULL;
    CREATE TABLE review_datasets (
      id text PRIMARY KEY, name text NOT NULL, manifest jsonb NOT NULL,
      actor text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
      archive_key text, archive_sha256 text);
    CREATE TABLE review_dataset_items (
      dataset_id text REFERENCES review_datasets(id), sample_id text NOT NULL, revision
        integer NOT NULL,
      split text NOT NULL CHECK(split IN ('train','val','test')),
      PRIMARY KEY(dataset_id,sample_id),
      FOREIGN KEY(sample_id,revision) REFERENCES review_revisions(sample_id,revision));

    CREATE FUNCTION review_guard_group() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF NEW.split <> OLD.split OR (OLD.test_locked AND NOT NEW.test_locked) THEN
        RAISE EXCEPTION 'review: splits immuables et tests geles' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER review_group_guard BEFORE UPDATE ON review_groups
      FOR EACH ROW EXECUTE FUNCTION review_guard_group();

    CREATE FUNCTION review_guard_video() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP='UPDATE' AND (NEW.group_id<>OLD.group_id OR NEW.source_key<>OLD.source_key OR
        NEW.id<>OLD.id) THEN
        RAISE EXCEPTION 'review: source et groupe immuables' USING ERRCODE='23514';
      END IF;
      IF TG_OP='INSERT' AND EXISTS(SELECT 1 FROM review_groups WHERE id=NEW.group_id AND
        test_locked) THEN
        RAISE EXCEPTION 'review: groupe test gele' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER review_video_guard BEFORE INSERT OR UPDATE ON review_videos
      FOR EACH ROW EXECUTE FUNCTION review_guard_video();

    CREATE FUNCTION review_guard_revision() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP='UPDATE' THEN
        IF
        ROW(NEW.sample_id,NEW.revision,NEW.state,NEW.label,NEW.box,NEW.recipe,NEW.actor,NEW.provenance,NEW.created_at)
          IS DISTINCT FROM
        ROW(OLD.sample_id,OLD.revision,OLD.state,OLD.label,OLD.box,OLD.recipe,OLD.actor,OLD.provenance,OLD.created_at)
          OR (OLD.crop_key IS NOT NULL AND ROW(NEW.crop_key,NEW.crop_sha256,NEW.quality)
             IS DISTINCT FROM ROW(OLD.crop_key,OLD.crop_sha256,OLD.quality)) THEN
          RAISE EXCEPTION 'review: historique immuable' USING ERRCODE='23514';
        END IF;
      ELSIF EXISTS(SELECT 1 FROM review_samples s JOIN review_frames f ON f.id=s.frame_id
        JOIN review_videos v ON v.id=f.video_id JOIN review_groups g ON g.id=v.group_id
        WHERE s.id=NEW.sample_id AND g.test_locked) THEN
          RAISE EXCEPTION 'review: annotations test gelees' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER review_revision_guard BEFORE INSERT OR UPDATE ON review_revisions
      FOR EACH ROW EXECUTE FUNCTION review_guard_revision();
    CREATE FUNCTION review_no_delete() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN RAISE EXCEPTION 'review: conservation historique requise' USING ERRCODE='23514';
        END $$;
    CREATE TRIGGER review_revision_no_delete BEFORE DELETE ON review_revisions
      FOR EACH ROW EXECUTE FUNCTION review_no_delete();
    CREATE FUNCTION review_dataset_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF ROW(NEW.id,NEW.name,NEW.manifest,NEW.actor,NEW.created_at)
        IS DISTINCT FROM ROW(OLD.id,OLD.name,OLD.manifest,OLD.actor,OLD.created_at)
        OR (OLD.archive_sha256 IS NOT NULL AND NEW.archive_sha256 IS DISTINCT FROM
        OLD.archive_sha256) THEN
        RAISE EXCEPTION 'review: snapshot immuable' USING ERRCODE='23514';
      END IF; RETURN NEW;
    END $$;
    CREATE TRIGGER review_dataset_immutable BEFORE UPDATE ON review_datasets
      FOR EACH ROW EXECUTE FUNCTION review_dataset_guard();
    CREATE TRIGGER review_dataset_no_delete BEFORE DELETE ON review_datasets
      FOR EACH ROW EXECUTE FUNCTION review_no_delete();
    CREATE TRIGGER review_dataset_item_immutable BEFORE UPDATE OR DELETE ON
        review_dataset_items
      FOR EACH ROW EXECUTE FUNCTION review_no_delete();
    CREATE TRIGGER review_frame_immutable BEFORE UPDATE OR DELETE ON review_frames
      FOR EACH ROW EXECUTE FUNCTION review_no_delete();
    CREATE TRIGGER review_import_immutable BEFORE UPDATE OR DELETE ON review_imports
      FOR EACH ROW EXECUTE FUNCTION review_no_delete();
    CREATE FUNCTION review_guard_sample() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF
        ROW(NEW.id,NEW.frame_id,NEW.original_box,NEW.original_crop_key,NEW.detector_identity,
        NEW.detection_score,NEW.predicted_label,NEW.classification_score,NEW.probabilities)
        IS DISTINCT FROM
        ROW(OLD.id,OLD.frame_id,OLD.original_box,OLD.original_crop_key,OLD.detector_identity,
        OLD.detection_score,OLD.predicted_label,OLD.classification_score,OLD.probabilities)
        OR EXISTS(SELECT 1 FROM review_frames f JOIN review_videos v ON v.id=f.video_id
        JOIN review_groups g ON g.id=v.group_id WHERE f.id=OLD.frame_id AND g.test_locked)
        THEN
        RAISE EXCEPTION 'review: source immuable ou groupe test gele' USING ERRCODE='23514';
      END IF; RETURN NEW;
    END $$;
    CREATE TRIGGER review_sample_guard BEFORE UPDATE ON review_samples
      FOR EACH ROW EXECUTE FUNCTION review_guard_sample();
    CREATE TRIGGER review_sample_no_delete BEFORE DELETE ON review_samples
      FOR EACH ROW EXECUTE FUNCTION review_no_delete();
    """)


def downgrade() -> None:
    op.execute("""
    ALTER TABLE review_samples DROP CONSTRAINT review_current_revision_fk;
    DROP TABLE review_dataset_items, review_datasets, review_operations, review_revisions,
      review_samples, review_similarities, review_frames, review_imports, review_videos,
      review_groups, review_species;
    DROP FUNCTION review_guard_group(),review_guard_video(),review_guard_revision(),
      review_no_delete(),review_dataset_guard(),review_guard_sample();
    """)
