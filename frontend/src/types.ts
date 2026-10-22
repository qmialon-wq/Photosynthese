export interface Box {
  x: number;
  y: number;
  w: number;
  h: number;
}
export interface Species {
  name: string;
  class_index: number;
  manifest_version: string;
}
export interface Operation {
  id: string;
  status: string;
  status_url: string;
}
export interface Quality {
  blurry?: boolean;
  too_small?: boolean;
  near_duplicate?: boolean;
}
export interface Sample {
  frame_index: number;
  id: string;
  video_id: string;
  original_name: string;
  revision: number;
  state: string;
  label: string | null;
  predicted_label: string | null;
  species_candidate: string | null;
  detection_score: number;
  classification_score: number | null;
  box: Box;
  original_box: Box;
  split: string;
  test_locked: boolean;
  render_status: string;
  quality: Quality | null;
  frame_quality: Quality;
  actor: string;
  provenance: Record<string, unknown>;
  created_at: string;
  render_operation_id?: string | null;
}
export interface Video {
  id: string;
  filename: string;
  video_key: string;
  sha256: string;
  species_candidate: string | null;
  status: string;
  created_at: string;
  metadata: {
    duration_seconds?: number;
    width?: number;
    height?: number;
    frames?: number;
    preview_key?: string;
  };
}
export interface Metrics {
  count?: number;
  accuracy?: number | null;
  macro_f1?: number | null;
  loss?: number;
  classes?: string[];
  confusion_matrix?: number[][];
  per_class?: Record<
    string,
    { support: number; precision: number; recall: number; f1: number }
  >;
  images?: Metrics;
  videos?: Metrics;
  validation?: Metrics;
  split?: string;
  human_validated?: boolean;
}
export interface Task extends Operation {
  kind: string;
  actor: string;
  created_at: string;
  finished_at: string | null;
  request: {
    video_id?: string;
    dataset_id?: string;
    model_name?: string;
    epochs_head?: number;
    epochs_finetune?: number;
  };
  progress: { current?: number; total?: number; stage?: string };
  cancel_requested: boolean;
  error: string | null;
  result: {
    video_id?: string;
    output?: string;
    run_id?: string;
    model_id?: string;
    metrics?: Metrics;
  } | null;
}
export interface Dataset {
  id: string;
  name: string;
  actor: string;
  created_at: string;
  archive_sha256: string | null;
  manifest?: {
    samples: Array<Sample & { group_id: string }>;
    classes: { version: string; classes: Array<{ name: string; id: number }> };
  };
}
export interface Model {
  id: string;
  name: string;
  checkpoint_key: string;
  sha256: string;
  active: boolean;
  created_at: string;
  metadata: {
    model_name: string;
    image_size: number;
    run_id?: string;
    label_provenance?: Record<string, unknown>;
  };
  metrics: Metrics;
}
export interface Run {
  run_id: string;
  status: string;
  updated_at: string;
  metadata: {
    best_macro_f1?: number;
    run_id?: string;
    phase?: string;
    epoch?: number;
    device?: string;
    gpu_peak_allocated_bytes?: number;
    gpu_total_memory_bytes?: number;
    label_provenance?: Record<string, unknown>;
  };
}
export interface Epoch {
  event_key: string;
  metrics: {
    phase: string;
    epoch: number;
    train_loss: number;
    validation: Metrics;
  };
}
export interface Dashboard {
  counts: { videos: number; species: number; pending: number; tasks: number };
  distribution: Array<{ label: string; count: number }>;
  latest_training: Run["metadata"] | null;
}
export interface Report {
  status: string;
  frames_decoded: number;
  detections: number;
  diagnostics: Record<string, number | string | null>;
  species: Array<{ species: string; estimated_tracks: number }>;
  frames: Array<{
    frame_index: number;
    time_seconds: number;
    detections: Array<{
      box: Box;
      detection_score: number;
      classification_score: number | null;
      label?: string;
      species?: string;
      state: string;
      track_id: number;
      classification: { label: string | null; score: number } | null;
    }>;
  }>;
}
