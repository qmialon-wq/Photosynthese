export const interventionLabels = {
  earthworks: "Terrassement",
  vegetation_removal: "Suppression de végétation",
  fencing: "Clôture",
  outdoor_lighting: "Éclairage extérieur",
  soil_sealing: "Imperméabilisation",
} as const;
export type Intervention = keyof typeof interventionLabels;
export interface ProjectProfile {
  area_m2?: number | null;
  land_type?: string;
  project_type?: string;
  locality?: string;
  details?: string;
  interventions?: Intervention[];
}
export interface PointLocation {
  latitude: number;
  longitude: number;
  revision: number;
  provenance: "map" | "numeric";
  actor: string;
  created_at: string;
}
export interface TerritorialAction {
  category: "avoid" | "reduce" | "investigate";
  project_action: string;
  issue: string;
  action: string;
  rationale: string;
  evidence_refs: string[];
  source_refs: string[];
  preconditions: string[];
  missing_information: string[];
  limitations: string[];
  evidence_status: "general_verification" | "conditional_proposal";
}
export interface TerritorialSource {
  id: string;
  title: string;
  url?: string;
  retrieved_at?: string;
  sha256?: string;
  text?: string;
  quote?: string;
  page?: number;
  relevance_reason?: string;
  limitation?: string;
  original_url?: string;
  role?: string;
  applicability?: string;
  design_alternative_ids?: string[];
}
export interface DesignAlternative {
  id: string;
  category: "avoid" | "reduce";
  title: string;
  proposal: string;
  project_change: string;
  conditions: string[];
  evidence_refs: string[];
  source_refs: string[];
  justification: {
    level: "exploratory" | "contextualized" | "scientifically_qualified";
    reason: string;
  };
  status: "conditional_design_option";
  limitations: string[];
}
export interface DesignProposal {
  project_action: Intervention;
  initial_intervention: string;
  issue: string;
  alternatives: DesignAlternative[];
}
export interface TerritorialAnalysis {
  rules_version: string;
  analysis_revision: number;
  facts: { id: string; kind: string; text: string; source_refs: string[] }[];
  project_concerns: {
    project_action: string;
    issue: string;
    evidence_refs: string[];
  }[];
  actions: TerritorialAction[];
  design_proposals?: DesignProposal[];
  unknowns: string[];
  limitations: string[];
  sources: TerritorialSource[];
  compensation: { status: "not_assessed" };
  documentary?: {
    status: string;
    base_query_id?: string;
    excerpt_count?: number;
  };
}
export interface TerritorialQuery {
  id: string;
  revision: number;
  status: "pending" | "complete" | "partial" | "failed";
  obsolete: boolean;
  input_sha256: string;
  inputs: {
    location: PointLocation;
    profile: ProjectProfile;
    profile_revision: number;
    observations: {
      sample_id: string;
      revision: number;
      species: string;
      state: string;
    }[];
  };
  layers: Record<
    string,
    {
      status: "success" | "empty" | "unavailable" | "error";
      retrieved_at: string;
      error?: string;
      sha256?: string;
      source_url: string;
      features: unknown[];
    }
  >;
  result: TerritorialAnalysis | null;
  created_at: string;
  documentary_task?: {
    status: string;
    result?: { status?: string; message?: string };
    error?: string;
  } | null;
  task_status?: string;
  task_error?: string;
}
export interface TerritorialContext {
  location: PointLocation | null;
  profile: ProjectProfile;
  profile_revision: number;
  query: TerritorialQuery | null;
}
