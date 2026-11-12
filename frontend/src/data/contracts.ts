/** Contrats de présentation des données enregistrées. Une absence reste explicite. */
export type SourceState =
  | "loading"
  | "success"
  | "empty"
  | "error"
  | "unconnected";
export interface Resource<T> {
  state: SourceState;
  data: T[];
  message: string;
  complete: boolean;
}
export type VideoStatus =
  | "validated"
  | "pending"
  | "unanalysed"
  | "unknown"
  | "ready"
  | "processing"
  | "no_detections"
  | "error";
export interface Video {
  id: string;
  filename: string;
  species: string;
  parcel: string;
  date: string;
  duration: string;
  durationSeconds?: number;
  status: VideoStatus;
  thumbnail?: "deer" | "fox" | "badger" | "boar";
  poster?: string;
  projectId?: string;
  source?: string;
  sourceStatus?: string;
}
export interface Project {
  id: string;
  name: string;
  videos: number | null;
  species: number | null;
  status: VideoStatus;
  project: string;
  landscape?: "forest" | "valley" | "wetland" | "meadow" | "bocage";
  videoIds?: string[];
  previewVideo?: {
    id: string;
    filename: string;
    source: string;
    poster?: string;
  };
  dossierStatus?: string;
  recommendations?: Recommendation[];
}
export interface Detection {
  id: string;
  label: string;
  confidence: number | null;
  bounds: { x: number; y: number; width: number; height: number };
  time?: number;
}
export interface AnalysisVideo {
  id: string;
  filename: string;
  species: string;
  kind: "poster" | "video" | "image";
  source?: string;
  poster?: string;
  posterSize?: string;
  posterPosition?: string;
  duration: number | null;
  width: number | null;
  height: number | null;
  detections: Detection[];
  videoId?: string;
  provenance?: "demo" | "real";
  state?: string;
  createdAt?: string;
  notice?: string;
  accessibleLabel?: string;
  playback?: "simulated" | "read-only";
}
export type ObservationQuality =
  | "clear"
  | "blurry"
  | "too_small"
  | "near_duplicate"
  | "unknown";
export interface Observation {
  id: string;
  number: number;
  filename: string;
  suggestedSpecies: string;
  assignedSpecies?: string;
  quality: ObservationQuality;
  protected: boolean;
  status: "review" | "validated";
  context: string;
  media: AnalysisVideo;
  videoId?: string;
  statusLabel?: string;
}
export interface Species {
  value: string;
  label: string;
}
export type DocumentKind = "PDF" | "DOCX" | "TXT";
export interface ScientificDocument {
  id: string;
  species: string;
  title: string;
  kind: DocumentKind | null;
  date: string;
  origin: "example" | "import" | "retrieval" | "source";
  filename?: string;
  speciesIds?: string[];
  url?: string;
  sourceStatus?: string;
  dateNote?: string;
}
export interface Statistic {
  icon: string;
  value: string;
  label: string;
  detail: string;
}
export interface Recommendation {
  id: string;
  title: string;
  description: string;
  projectId?: string;
  priority?: string;
}
export interface HomeSummary {
  overview: Statistic[];
  videoOverview: Statistic[];
  score: number | null;
  indicators: { icon: string; label: string; value: number }[];
  recommendations: Recommendation[];
  latestAnalyses: {
    id: string;
    name: string;
    date: string;
    status: string;
    validated: boolean;
    species: number | null;
    observations: number | null;
    thumbnail?: string;
    source?: string;
    poster?: string;
  }[];
}
export interface Collections {
  videos: Video;
  projects: Project;
  observations: Observation;
  analyses: AnalysisVideo;
  documents: ScientificDocument;
  species: Species;
}
export type Snapshot = { [K in keyof Collections]: Resource<Collections[K]> };
export interface DataProvider {
  id: string;
  load(
    signal: AbortSignal,
    publish: <K extends keyof Collections>(
      key: K,
      resource: Resource<Collections[K]>,
    ) => void,
  ): Promise<void>;
  report?(id: string, signal: AbortSignal): Promise<Detection[]>;
}
export function resource<T>(
  data: T[] = [],
  state: SourceState = data.length ? "success" : "empty",
  message = "",
  complete = true,
): Resource<T> {
  return { data, state, message, complete };
}
export function emptySnapshot(
  state: SourceState = "loading",
  message = "",
): Snapshot {
  return {
    videos: resource([], state, message),
    projects: resource([], state, message),
    observations: resource([], state, message),
    analyses: resource([], state, message),
    documents: resource([], state, message),
    species: resource([], state, message),
  };
}
