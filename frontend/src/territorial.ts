import type { CitationSource } from "./source-links";

export interface TerritorialReport {
  status: string;
  corpus_snapshot_at?: string;
  ledger?: CitationSource[];
  coverage: {
    documents_total: number;
    documents_read: number;
    chunks_read?: number;
    reading_mode?: string;
    reading_method?: string;
    excerpts_selected?: number;
    batches_rejected?: Array<{ batch: number; reason: string }>;
    documents_pending_review?: number;
    unreadable_ids?: string[];
    complete?: boolean;
    new_documents_since_snapshot?: number;
  };
  pages?: Array<{
    title: string;
    paragraphs: Array<{ text: string; citations: string[] }>;
  }>;
  actions?: Array<{
    title: string;
    action: string;
    location: string;
    rationale: string;
    conditions: string;
    priority: string;
    monitoring: string;
    citations: string[];
  }>;
}
