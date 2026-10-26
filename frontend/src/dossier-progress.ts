export interface DossierProgress {
  phase: string;
  reading_mode?: string;
  generation_started_at?: string;
  detailed_tracking: boolean;
  documents_started: number;
  documents_done?: number;
  documents_total?: number;
  chunks_read: number;
  chunks_total?: number;
  current_document?: string | null;
  current_document_chunks_read: number;
  current_document_chunks_total?: number;
  groups_done?: number;
  groups_total?: number;
  pages_done: number;
  pages_total: number;
  elapsed_seconds: number;
  seconds_since_activity: number;
  last_activity_at: string;
  recent: Array<{ message: string; at: string }>;
}
