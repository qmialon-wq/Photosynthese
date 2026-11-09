import { api, apiUrl, ApiError } from "../api";
import { acceptSession, type Session } from "../auth-state";
import type { Video as ApiVideo, Sample, Task, Report } from "../types";
import type { ScientificDocument as ApiDocument } from "../documents";
import { externalUrl } from "../documents";
import {
  resource,
  type DataProvider,
  type Collections,
  type Resource,
  type Detection,
  type AnalysisVideo,
  type Project,
  type Observation,
  type ScientificDocument,
  type Video,
} from "./contracts";

type Request = <T>(path: string, options?: RequestInit) => Promise<T>;
type Corpus = {
  id: string;
  video_count: number;
  latest_dossier_id: string | null;
};
type CorpusDetail = {
  id: string;
  videos: { video_id: string; filename: string }[];
  profile: { profile: { locality?: string; project_type?: string } } | null;
  dossier: {
    status: string;
    result?: { confirmed_species?: { name: string }[] } | null;
  } | null;
};
const encoded = encodeURIComponent;
const calendar = (value: string | null | undefined) =>
  value && Number.isFinite(Date.parse(value))
    ? new Date(value).toLocaleDateString("fr-FR")
    : "";
function failure<T>(error: unknown): Resource<T> {
  if (
    error instanceof ApiError &&
    [404, 405, 501, 502, 503, 504].includes(error.status)
  )
    return resource(
      [],
      "unconnected",
      "Fonctionnalité non connectée : source indisponible.",
    );
  if (error instanceof ApiError && [401, 403].includes(error.status))
    return resource(
      [],
      "error",
      error.status === 401
        ? "Connexion requise pour consulter les données réelles."
        : "Accès non autorisé à cette source.",
    );
  return resource(
    [],
    "error",
    error instanceof TypeError
      ? "Source inaccessible. Vérifiez la connexion au serveur."
      : "Impossible de charger cette source. Réessayez.",
  );
}
function rows<T>(value: unknown): T[] {
  if (
    !Array.isArray(value) ||
    value.some(
      (row) => !row || typeof row !== "object" || typeof row.id !== "string",
    )
  )
    throw new Error("Réponse de source invalide");
  return value as T[];
}
export function adaptVideo(row: ApiVideo): Video {
  if (typeof row.filename !== "string") throw new Error("Vidéo invalide");
  const seconds = row.metadata?.duration_seconds;
  return {
    id: row.id,
    filename: row.filename,
    species: row.species_candidate || "",
    parcel: "",
    date: calendar(row.created_at),
    duration:
      seconds == null
        ? ""
        : `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`,
    ...(seconds != null ? { durationSeconds: seconds } : {}),
    status: ["ready", "processing", "no_detections", "error"].includes(
      row.status,
    )
      ? (row.status as Video["status"])
      : "unknown",
    sourceStatus: row.status,
    source: apiUrl(`/console/videos/${encoded(row.id)}/file`),
  };
}
function media(row: ApiVideo): AnalysisVideo {
  return {
    id: row.id,
    videoId: row.id,
    filename: row.filename,
    species: row.species_candidate || "",
    kind: "video",
    source: apiUrl(`/console/videos/${encoded(row.id)}/file`),
    duration: row.metadata?.duration_seconds ?? null,
    width: row.metadata?.width ?? null,
    height: row.metadata?.height ?? null,
    detections: [],
    provenance: "real",
    playback: "read-only",
    notice: "VIDÉO ENREGISTRÉE · CONSULTATION",
    accessibleLabel: "Lecteur vidéo enregistré",
  };
}
export function adaptObservation(row: Sample, index: number): Observation {
  if (
    typeof row.original_name !== "string" ||
    !Number.isInteger(row.frame_index)
  )
    throw new Error("Observation invalide");
  const quality = row.quality || row.frame_quality;
  return {
    id: row.id,
    number: index + 1,
    videoId: row.video_id,
    filename: row.original_name,
    suggestedSpecies: row.predicted_label || row.species_candidate || "",
    assignedSpecies: row.label || undefined,
    quality: quality?.blurry
      ? "blurry"
      : quality?.too_small
        ? "too_small"
        : quality?.near_duplicate
          ? "near_duplicate"
          : quality
            ? "clear"
            : "unknown",
    protected: row.test_locked,
    status: ["validated", "corrected"].includes(row.state)
      ? "validated"
      : "review",
    statusLabel: row.state === "rejected" ? "Rejetée" : undefined,
    context: `Image ${row.frame_index}`,
    media: {
      id: row.id,
      filename: row.original_name,
      species: row.label || row.predicted_label || "",
      kind: "image",
      poster: apiUrl(`/review/samples/${encoded(row.id)}/images/original`),
      duration: null,
      width: null,
      height: null,
      detections: [],
      provenance: "real",
      playback: "read-only",
      notice: "OBSERVATION ENREGISTRÉE",
      accessibleLabel: "Image de l’observation enregistrée",
    },
  };
}
export function adaptDocument(row: ApiDocument): ScientificDocument {
  if (typeof row.title !== "string") throw new Error("Document invalide");
  const ids = row.species_links?.map((link) => link.species) || [];
  const format = row.assets?.[0]?.format?.toUpperCase();
  return {
    id: row.id,
    title: row.title,
    species: ids[0] || "",
    speciesIds: ids,
    date: calendar(row.published_date),
    kind:
      format === "PDF" || format === "DOCX" || format === "TXT" ? format : null,
    origin: "source",
    url: externalUrl(row.url),
    sourceStatus: row.status,
  };
}
/** Lecture seule : toutes les requêtes, y compris les rapports, utilisent GET. */
export class RealDataProvider implements DataProvider {
  readonly id = "real:same-origin-api";
  constructor(private readonly request: Request = api) {}
  private async list<T>(path: string, signal: AbortSignal): Promise<T[]> {
    const result: T[] = [];
    for (let offset = 0; offset < 20000; offset += 200) {
      const batch = rows<T>(
        await this.request<unknown>(
          `${path}${path.includes("?") ? "&" : "?"}limit=200&offset=${offset}`,
          { method: "GET", signal },
        ),
      );
      result.push(...batch);
      if (batch.length < 200) return result;
    }
    throw new Error("Source trop volumineuse pour une lecture complète");
  }
  async load(
    signal: AbortSignal,
    publish: Parameters<DataProvider["load"]>[1],
  ) {
    const loaded: Partial<{
      [K in keyof Collections]: Resource<Collections[K]>;
    }> = {};
    try {
      const session = await this.request<Session>("/auth/me", {
        method: "GET",
        signal,
      });
      if (signal.aborted) return;
      if (!session?.user?.id) throw new Error("Session invalide");
      acceptSession(session);
    } catch (error) {
      if (!signal.aborted)
        for (const key of [
          "videos",
          "projects",
          "observations",
          "analyses",
          "documents",
          "species",
        ] as const)
          publish(key, failure(error));
      return;
    }
    async function load<K extends keyof Collections>(
      key: K,
      operation: () => Promise<Resource<Collections[K]>>,
    ) {
      try {
        const result = await operation();
        if (!signal.aborted) {
          Object.assign(loaded, { [key]: result });
          publish(key, result);
        }
      } catch (error) {
        if (!signal.aborted) publish(key, failure(error));
      }
    }
    const videos = this.list<ApiVideo>("/console/videos", signal);
    // Chaque source est indépendante : l’échec du corpus n’efface pas les vidéos accessibles.
    await Promise.all([
      load("videos", async () => resource((await videos).map(adaptVideo))),
      load("observations", async () =>
        resource(
          (await this.list<Sample>("/review/samples", signal)).map(
            adaptObservation,
          ),
        ),
      ),
      load("documents", async () =>
        resource(
          (
            await this.list<ApiDocument>("/documents?stored_only=true", signal)
          ).map(adaptDocument),
        ),
      ),
      load("species", async () => {
        const data = await this.request<{ name: string }[]>("/review/species", {
          method: "GET",
          signal,
        });
        if (
          !Array.isArray(data) ||
          data.some((s) => typeof s.name !== "string")
        )
          throw new Error("Catalogue invalide");
        return resource(data.map((s) => ({ value: s.name, label: s.name })));
      }),
      load("projects", async () => {
        const list = rows<Corpus>(
          await this.request("/parcels/corpora", { method: "GET", signal }),
        );
        const projects: Project[] = [];
        // Lecture bornée et séquentielle des profils ; aucun dossier n’est créé.
        for (const row of list) {
          const detail = await this.request<CorpusDetail>(
            `/parcels/corpora/${encoded(row.id)}`,
            { method: "GET", signal },
          );
          if (!Array.isArray(detail.videos))
            throw new Error("Dossier invalide");
          projects.push({
            id: row.id,
            name: detail.profile?.profile.locality || `Dossier ${row.id}`,
            videos: detail.videos.length,
            videoIds: detail.videos.map((v) => v.video_id),
            species: detail.dossier?.result?.confirmed_species?.length ?? null,
            status: "unknown",
            project: detail.profile?.profile.project_type || "",
          });
        }
        return resource(
          projects,
          projects.length ? "success" : "empty",
          list.length === 100
            ? "Les 100 dossiers les plus récents sont affichés ; le total n’est pas disponible."
            : "",
          list.length < 100,
        );
      }),
      load("analyses", async () => {
        const tasks = rows<Task>(
          await this.request("/console/tasks?kind=analysis&limit=200", {
            method: "GET",
            signal,
          }),
        );
        const knownVideos = await videos.catch(() => [] as ApiVideo[]);
        const analyses = tasks
          .filter((task) => task.kind === "analysis")
          .map((task) => {
            const video = knownVideos.find(
              (v) => v.id === task.request.video_id,
            );
            return {
              ...(video
                ? media(video)
                : {
                    id: task.id,
                    filename: "",
                    species: "",
                    kind: "poster" as const,
                    duration: null,
                    width: null,
                    height: null,
                    detections: [],
                    provenance: "real" as const,
                    playback: "read-only" as const,
                    notice: "ANALYSE ENREGISTRÉE",
                    accessibleLabel: "Analyse sans média consultable",
                  }),
              id: task.id,
              videoId: task.request.video_id,
              state: task.status,
              createdAt: task.created_at,
              ...(task.status === "completed"
                ? {
                    kind: "video" as const,
                    source: apiUrl(
                      `/console/tasks/${encoded(task.id)}/artifacts/video`,
                    ),
                  }
                : {}),
            };
          });
        return resource(
          analyses,
          analyses.length ? "success" : "empty",
          tasks.length === 200
            ? "Les 200 analyses les plus récentes sont affichées."
            : "",
          tasks.length < 200,
        );
      }),
    ]);
    if (signal.aborted) return;
    if (loaded.videos && loaded.projects) {
      publish("videos", {
        ...loaded.videos,
        data: loaded.videos.data.map((video) => {
          const memberships = loaded.projects!.data.filter((project) =>
            project.videoIds?.includes(video.id),
          );
          return {
            ...video,
            parcel: memberships.map((project) => project.name).join(", "),
            projectId: memberships.length === 1 ? memberships[0].id : undefined,
          };
        }),
      });
    }
    if (
      loaded.projects &&
      loaded.observations?.complete &&
      ["success", "empty"].includes(loaded.observations.state)
    ) {
      publish("projects", {
        ...loaded.projects,
        data: loaded.projects.data.map((project) => ({
          ...project,
          species:
            project.species ??
            new Set(
              loaded
                .observations!.data.filter(
                  (observation) =>
                    project.videoIds?.includes(observation.videoId || "") &&
                    observation.status === "validated",
                )
                .map((observation) => observation.assignedSpecies)
                .filter(Boolean),
            ).size,
        })),
      });
    }
  }
  async report(id: string, signal: AbortSignal): Promise<Detection[]> {
    const report = await this.request<Report>(
      `/console/tasks/${encoded(id)}/artifacts/report`,
      { method: "GET", signal },
    );
    if (!Array.isArray(report.frames)) throw new Error("Rapport invalide");
    return report.frames.flatMap((frame) =>
      frame.detections.map((d, index) => ({
        id: `${frame.frame_index}-${index}`,
        label:
          d.classification?.label ||
          d.label ||
          d.species ||
          "Animal non identifié",
        confidence: d.classification?.score ?? d.classification_score ?? null,
        time: frame.time_seconds,
        bounds: { x: d.box.x, y: d.box.y, width: d.box.w, height: d.box.h },
      })),
    );
  }
}
