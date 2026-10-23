export interface Species {
  name: string;
  scientific_name: string;
  display_name: string;
  documents_count: number;
  selected_count: number;
}
export interface SearchProfiles {
  version: string;
  activities: { value: string; label: string }[];
}
export interface SpeciesLink {
  species: string;
  enabled: boolean;
  available: boolean;
}
export interface ScientificDocument {
  id: string;
  title: string;
  authors: string[];
  doi: string | null;
  published_date: string | null;
  abstract: string | null;
  url: string | null;
  status: string;
  relevance: string;
  quality: string;
  language: string | null;
  species_links: SpeciesLink[];
  metadata?: {
    screening?: { focus: string; candidate: boolean };
    translation_fr?: {
      status: string;
      source_title?: string;
      title?: string;
      abstract?: string | null;
      pages_done?: number;
      pages_total?: number;
      error?: string;
    };
  };
  assets?: { id: string; format: string; license: string; sha256: string }[];
  provenance?: { source: string; observed_at: string }[];
  selection_history?: {
    species: string;
    enabled: boolean;
    actor: string;
    created_at: string;
  }[];
}
export interface DocumentTask {
  id: string;
  kind: string;
  status: string;
  error: string | null;
  created_at: string;
  request: { search?: { species: string[] }; collection_species?: string };
  result: {
    observed?: number;
    errors?: number;
    inaccessible?: number;
    filtered_out?: number;
    downloaded?: number;
  } | null;
}
export interface DocumentPage {
  asset_id: string;
  page_number: number;
  clean_text: string;
  translated_text?: string | null;
  language: string;
  references_data: { text?: string; url?: string }[];
}
export const documentStatus: Record<string, string> = {
  discovered: "Métadonnées disponibles",
  imported: "Texte à vérifier",
  indexed: "Texte consultable",
  rejected: "Rejeté",
  inaccessible: "Texte intégral inaccessible",
  queued: "En attente",
  running: "En cours",
  completed: "Terminé",
  partial: "Terminé avec réserves",
  error: "En erreur",
};
export function externalUrl(value: string | null): string | undefined {
  if (!value) return undefined;
  try {
    const url = new URL(value);
    return ["https:", "http:"].includes(url.protocol) ? url.href : undefined;
  } catch {
    return undefined;
  }
}
