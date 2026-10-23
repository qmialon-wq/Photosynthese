"""Corpus documentaire par espèce et décisions de sélection traçables."""

from alembic import op

revision = "0007_document_species"
down_revision = "0006_scientific_documents"
branch_labels = depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE document_species_catalog (
      name text PRIMARY KEY,scientific_name text NOT NULL UNIQUE,display_name text NOT NULL,
      class_index integer NOT NULL UNIQUE);
    INSERT INTO document_species_catalog VALUES
      ('chevreuil','Capreolus capreolus','Chevreuil',0),
      ('sanglier','Sus scrofa','Sanglier',1),
      ('buse','Buteo buteo','Buse variable',2),
      ('pigeons','Columba palumbus','Pigeon ramier',3),
      ('martres','Martes martes','Martre',4),
      ('renards','Vulpes vulpes','Renard',5),
      ('blaireaux','Meles meles','Blaireau',6),
      ('chouette','Strix aluco','Chouette hulotte',7),
      ('geai','Garrulus glandarius','Geai des chênes',8),
      ('faisans','Phasianus colchicus','Faisan',9);
    CREATE TABLE document_species (
      document_id uuid REFERENCES scientific_documents(id),
      species text REFERENCES document_species_catalog(name),
      enabled boolean NOT NULL DEFAULT false,
      origin text NOT NULL CHECK(origin IN ('discovery','human')),
      actor text NOT NULL,updated_at timestamptz NOT NULL DEFAULT now(),
      PRIMARY KEY(document_id,species));
    CREATE TABLE document_selection_history (
      id bigserial PRIMARY KEY,document_id uuid REFERENCES scientific_documents(id),
      species text REFERENCES document_species_catalog(name),enabled boolean NOT NULL,
      actor text NOT NULL,created_at timestamptz NOT NULL DEFAULT now());
    CREATE INDEX document_species_lookup ON document_species(species,enabled,document_id);
    INSERT INTO document_species(document_id,species,origin,actor)
      SELECT DISTINCT d.id,c.name,'discovery','migration'
      FROM document_events e JOIN document_tasks t ON t.id=e.task_id
      JOIN scientific_documents d ON d.id=e.document_id
      CROSS JOIN LATERAL jsonb_array_elements_text(
        coalesce(t.request#>'{search,species}','[]'::jsonb)) term(value)
      JOIN document_species_catalog c
        ON lower(term.value) IN (lower(c.name),lower(c.scientific_name))
      WHERE e.stage='discovery' AND d.merged_into IS NULL ON CONFLICT DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("DROP TABLE document_selection_history,document_species,document_species_catalog")
