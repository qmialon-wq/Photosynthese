export const corpusSpecies = [
  { value: "renard", label: "Renard" },
  { value: "chevreuil", label: "Chevreuil" },
  { value: "sanglier", label: "Sanglier" },
  { value: "blaireau", label: "Blaireau" },
  { value: "cerf-elaphe", label: "Cerf élaphe" },
];
export type DemoDocumentKind = "PDF" | "DOCX" | "TXT";
export type DemoScientificDocument = {
  id: string;
  species: string;
  title: string;
  kind: DemoDocumentKind;
  date: string;
  origin: "example" | "import" | "retrieval";
  filename?: string;
};
export type DemoRetrievalTask = {
  species: string[];
  status: "queued" | "running" | "completed";
  progress: number;
};
export const retrievalLabels = {
  queued: "En attente",
  running: "En cours",
  completed: "Terminé",
};
export const retrievalQueueDelay = 700;
export const retrievalTickDuration = 350;
export const retrievalSteps = [18, 38, 59, 78, 94, 100];
export const documentPageSize = 2;
export const fictitiousDocumentDate = "12 mars 2025";
export function corpusSpeciesLabel(species: string) {
  return (
    corpusSpecies.find((option) => option.value === species)?.label || species
  );
}

// Renard reste vide. Ces exemples ne sont pas des titres de publications authentiques.
export const demoScientificDocuments: DemoScientificDocument[] = [
  ...Array.from({ length: 5 }, (_, index) => ({
    id: `example-chevreuil-${index + 1}`,
    species: "chevreuil",
    title: `Exemple fictif ${String(index + 1).padStart(2, "0")} — Chevreuil`,
    kind: (["PDF", "DOCX", "TXT"] as const)[index % 3],
    date: fictitiousDocumentDate,
    origin: "example" as const,
  })),
  ...Array.from({ length: 2 }, (_, index) => ({
    id: `example-sanglier-${index + 1}`,
    species: "sanglier",
    title: `Exemple fictif ${index + 1} — Sanglier`,
    kind: "PDF" as const,
    date: fictitiousDocumentDate,
    origin: "example" as const,
  })),
  {
    id: "example-blaireau-1",
    species: "blaireau",
    title: "Exemple fictif 01 — Blaireau",
    kind: "TXT",
    date: fictitiousDocumentDate,
    origin: "example",
  },
];
export function documentsForSpecies(
  documents: DemoScientificDocument[],
  species: string,
) {
  return documents.filter((document) => document.species === species);
}
export function documentSpeciesOptions(documents: DemoScientificDocument[]) {
  return corpusSpecies.map((option) => {
    const count = documentsForSpecies(documents, option.value).length;
    return {
      value: option.value,
      label: `${option.label} · ${count} document${count === 1 ? "" : "s"}`,
    };
  });
}
export function currentDocumentSelection(
  visible: DemoScientificDocument[],
  selected: ReadonlySet<string>,
) {
  return visible.filter((document) => selected.has(document.id));
}
export function removePreviewDocuments(
  documents: DemoScientificDocument[],
  visible: DemoScientificDocument[],
  selected: ReadonlySet<string>,
) {
  const ids = new Set(
    currentDocumentSelection(visible, selected).map((document) => document.id),
  );
  return documents.filter((document) => !ids.has(document.id));
}
export function importedDocumentKind(
  filename: string,
): DemoDocumentKind | null {
  const match = filename.match(/\.(pdf|docx|txt)$/i);
  return match ? (match[1].toUpperCase() as DemoDocumentKind) : null;
}
export function retrievalExampleDocuments(
  species: string[],
  run: number,
): DemoScientificDocument[] {
  return corpusSpecies
    .filter((option) => species.includes(option.value))
    .map((option) => ({
      id: `retrieval-${run}-${option.value}`,
      species: option.value,
      title: `Exemple fictif — ${option.label} · simulation ${run}`,
      kind: "PDF",
      date: fictitiousDocumentDate,
      origin: "retrieval",
    }));
}
