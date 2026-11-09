import { ApiError } from "../api";
import type {
  ScientificDocument as DocumentView,
  Video as VideoView,
  Project as ProjectView,
} from "../data/contracts";
import type { DataModeStore } from "../data/data-mode";
import type { User } from "../auth-state";
import type { Dataset, Metrics, Model, Sample, Video } from "../types";
import type { ScientificDocument } from "../documents";
import { corpusSpecies } from "../data/document-preview";
import squirrel from "../assets/squirrel-local.mp4";
import deer from "../assets/analysis-deer.png";

type Body = Record<string, unknown>;
type DemoTask = {
  id: string;
  kind: string;
  status: string;
  actor: string;
  created_at: string;
  finished_at: string | null;
  request: Body;
  progress: { current: number; total: number; stage: string };
  cancel_requested: boolean;
  error: string | null;
  result: Body | null;
  started: number;
  finish?: () => void;
  pendingResult?: Body;
};
const date = "2026-11-01T10:00:00Z";
const metrics: Metrics = {
  count: 2,
  accuracy: 1,
  macro_f1: 1,
  human_validated: true,
  classes: ["chevreuil", "renard"],
  confusion_matrix: [
    [1, 0],
    [0, 1],
  ],
};
const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T;

/** Adaptateur local des contrats existants. Aucun fetch, aucun stockage persistant. */
export class AdminDemoProvider {
  private serial = 0;
  private seeded = false;
  private users: User[] = [];
  private erasures: {
    id: string;
    user_id: string;
    status: string;
    requested_at: string;
    note: string;
  }[] = [];
  private models: Model[] = [];
  private datasets: Dataset[] = [];
  private tasks: DemoTask[] = [];
  private uploads = new Map<string, { filename: string; approved: boolean }>();
  private objectUrls = new Map<string, string>();
  constructor(
    private readonly store: DataModeStore,
    private readonly now = Date.now,
  ) {
    this.reset();
  }
  reset() {
    for (const url of this.objectUrls?.values() || []) URL.revokeObjectURL(url);
    this.objectUrls?.clear();
    this.uploads?.clear();
    this.serial = 0;
    this.seeded = false;
    this.users = [
      {
        id: "demo-account-1",
        display_name: "Camille Démonstration",
        email: "camille@example.test",
        role: "admin",
        created_at: date,
        deleted_at: null,
      },
      {
        id: "demo-account-2",
        display_name: "Alex Démonstration",
        email: "alex@example.test",
        role: "client",
        created_at: date,
        deleted_at: null,
      },
      {
        id: "demo-account-3",
        display_name: "Compte fictif archivé",
        email: null,
        role: "client",
        created_at: date,
        deleted_at: date,
      },
    ];
    this.erasures = [
      {
        id: "demo-erasure-1",
        user_id: "demo-account-3",
        status: "pending",
        requested_at: date,
        note: "Exemple fictif de suivi. Aucune donnée personnelle réelle.",
      },
    ];
    this.models = [
      this.model("demo-model-1", "Normandie · modèle de démonstration", true),
      this.model("demo-model-2", "Lisières · modèle de démonstration", false),
    ];
    this.datasets = [
      this.dataset("demo-dataset-1", "Normandie · version fictive 1"),
    ];
    this.tasks = [
      this.completed(
        "demo-run-1",
        "training",
        { dataset_id: "demo-dataset-1", model_name: "convnext_tiny" },
        { run_id: "demo-run-1", model_id: "demo-model-1", metrics },
      ),
      this.completed(
        "demo-evaluation-1",
        "evaluation",
        { dataset_id: "demo-dataset-1", model_id: "demo-model-1" },
        { metrics },
      ),
      this.completed(
        "demo-analysis-1",
        "analysis",
        { video_id: "demo-video-124" },
        { video_id: "demo-video-124", output: "simulation" },
      ),
    ];
  }
  private id(kind: string) {
    return `demo-${kind}-local-${++this.serial}`;
  }
  private model(id: string, name: string, active: boolean): Model {
    return {
      id,
      name,
      active,
      status: active ? "active" : "candidate",
      family: "supervised",
      checkpoint_key: `simulation/${id}/best.pt`,
      sha256: "d".repeat(64),
      created_at: date,
      metadata: { model_name: "convnext_tiny", image_size: 224 },
      metrics: clone(metrics),
    };
  }
  private dataset(id: string, name: string, request: Body = {}): Dataset {
    const excluded = new Set((request.exclude_groups as string[]) || []),
      flags = new Set((request.exclude_quality as string[]) || []);
    const splits = new Map<string, string>();
    const samples = this.store.data.observations.data
      .filter(
        (o) =>
          o.status === "validated" &&
          !excluded.has(o.videoId || "") &&
          !flags.has(o.quality),
      )
      .map((o, i) => {
        const key = o.videoId || o.id;
        if (!splits.has(key))
          splits.set(key, splits.size % 2 ? "val" : "train");
        return {
          id: o.id,
          video_id: o.videoId || "",
          original_name: o.filename,
          frame_index: i,
          revision: 1,
          state: "validated",
          label: o.assignedSpecies || o.suggestedSpecies,
          predicted_label: o.suggestedSpecies,
          species_candidate: o.suggestedSpecies,
          detection_score: 0.94,
          classification_score: 0.94,
          box: { x: 0, y: 0, w: 1, h: 1 },
          original_box: { x: 0, y: 0, w: 1, h: 1 },
          split: splits.get(key)!,
          test_locked: false,
          render_status: "ready",
          quality: { [o.quality]: true },
          frame_quality: {},
          actor: "Démonstration locale",
          provenance: { simulation: true },
          created_at: date,
          group_id: o.videoId || "",
        } satisfies Sample & { group_id: string };
      });
    return {
      id,
      name,
      actor: "Démonstration locale",
      created_at: date,
      archive_sha256: "d".repeat(64),
      manifest: {
        samples: clone(samples),
        classes: {
          version: "demo-v1",
          classes: [
            { name: "chevreuil", id: 0 },
            { name: "renard", id: 1 },
          ],
        },
      },
    };
  }
  private completed(
    id: string,
    kind: string,
    request: Body,
    result: Body,
  ): DemoTask {
    return {
      id,
      kind,
      request,
      result,
      status: "completed",
      actor: "Démonstration locale",
      created_at: date,
      finished_at: date,
      progress: { current: 100, total: 100, stage: "Simulation terminée" },
      cancel_requested: false,
      error: null,
      started: 0,
    };
  }
  private operation(
    kind: string,
    request: Body,
    finish?: () => void,
    result: Body = {},
  ) {
    const task = this.completed(this.id(kind), kind, clone(request), result);
    task.pendingResult = clone(result);
    task.result = null;
    task.status = "queued";
    task.finished_at = null;
    task.progress = { current: 0, total: 100, stage: "Simulation en attente" };
    task.started = this.now();
    task.finish = finish;
    this.tasks.unshift(task);
    return {
      id: task.id,
      status: "queued",
      status_url: `/console/tasks/${task.id}`,
    };
  }
  private advance() {
    for (const task of this.tasks) {
      if (!["queued", "running"].includes(task.status)) continue;
      const value = Math.min(100, Math.floor((this.now() - task.started) / 25));
      task.status =
        value < 10 ? "queued" : value < 100 ? "running" : "completed";
      task.progress = {
        current: value,
        total: 100,
        stage:
          value === 100
            ? "Simulation locale terminée"
            : "Progression simulée · aucun worker réel",
      };
      if (value === 100) {
        task.finished_at = new Date(this.now()).toISOString();
        task.finish?.();
        task.result = task.pendingResult || {};
        task.pendingResult = undefined;
        task.finish = undefined;
      }
    }
  }
  private videos(): Video[] {
    return this.store.data.videos.data.map((video) => {
      const media = this.store.data.analyses.data.find(
        (analysis) => analysis.videoId === video.id,
      );
      return {
        id: video.id,
        filename: video.filename,
        video_key: `simulation/${video.filename}`,
        sha256: video.id.padEnd(64, "d"),
        species_candidate: video.species.toLocaleLowerCase("fr"),
        status: "ready",
        created_at: date,
        metadata: {
          duration_seconds: video.durationSeconds,
          width: media?.width || undefined,
          height: media?.height || undefined,
          presentation_only: media?.kind !== "video",
          poster_url: media?.poster,
        },
      };
    });
  }
  private importVideo(filename: string, kind: string) {
    const id = this.id("video");
    const video: VideoView = {
      id,
      filename,
      species: "Non déterminée",
      parcel: "Import de démonstration",
      date: "1 novembre 2026",
      duration: "Non mesurée",
      status: "ready",
    };
    return this.operation(
      kind,
      { filename },
      () =>
        this.store.replace("videos", [
          video,
          ...(clone(this.store.data.videos.data) as VideoView[]),
        ]),
      { video_id: id },
    );
  }
  private documents(): ScientificDocument[] {
    return this.store.data.documents.data.map((doc) => ({
      id: doc.id,
      title: doc.title,
      authors: ["Auteur fictif · démonstration"],
      doi: null,
      published_date: null,
      abstract:
        "Exemple local de présentation, sans contenu scientifique authentique.",
      url: null,
      status: "indexed",
      relevance: "relevant",
      quality: "acceptable",
      language: "fr",
      species_links: (doc.speciesIds || [doc.species]).map((species) => ({
        species,
        enabled: true,
        available: true,
      })),
      assets: [],
    }));
  }
  private sharedDocuments(): DocumentView[] {
    return clone(this.store.data.documents.data) as DocumentView[];
  }
  private sharedProjects(): ProjectView[] {
    return clone(this.store.data.projects.data) as ProjectView[];
  }
  private task(id: string) {
    const task = this.tasks.find((task) => task.id === id);
    if (!task) throw new ApiError("Tâche de démonstration introuvable", 404);
    return task;
  }
  private report() {
    return {
      status: "completed",
      frames_decoded: 2,
      detections: 2,
      diagnostics: { gpu_elapsed_seconds: null },
      species: [{ species: "chevreuil", estimated_tracks: 1 }],
      frames: [
        {
          frame_index: 1,
          time_seconds: 1,
          detections: [
            {
              box: { x: 0.645, y: 0.36, w: 0.285, h: 0.395 },
              detection_score: 0.96,
              classification_score: 0.94,
              classification: { label: "chevreuil", score: 0.94 },
              state: "classified",
              track_id: 1,
            },
          ],
        },
      ],
    };
  }
  url(path: string): string {
    if (path.endsWith("/file") || path.endsWith("/artifacts/video"))
      return squirrel;
    if (path.includes("/images/")) return deer;
    const existing = this.objectUrls.get(path);
    if (existing) return existing;
    const value = path.endsWith("/artifacts/report")
      ? this.report()
      : {
          mode: "demo",
          notice:
            "Document de démonstration. Aucun artefact métier réel n’a été produit.",
          path,
        };
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
    );
    this.objectUrls.set(path, url);
    return url;
  }
  async request(path: string, options: RequestInit = {}): Promise<unknown> {
    if (options.signal?.aborted)
      throw new DOMException("Aborted", "AbortError");
    if (!this.seeded) {
      this.datasets = [
        this.dataset("demo-dataset-1", "Normandie · version fictive 1"),
      ];
      this.seeded = true;
    }
    this.advance();
    const url = new URL(path, "https://symbiose.invalid"),
      p = url.pathname,
      method = (options.method || "GET").toUpperCase();
    const body: Body =
      typeof options.body === "string"
        ? (JSON.parse(options.body) as Body)
        : {};
    const offset = Number(url.searchParams.get("offset") || 0),
      limit = Number(url.searchParams.get("limit") || 50);
    let match: RegExpMatchArray | null;
    if (method === "GET") {
      if (p === "/admin/users") {
        const q = (url.searchParams.get("q") || "").toLowerCase();
        return clone(
          this.users.filter(
            (u) =>
              (url.searchParams.get("include_deleted") === "true" ||
                !u.deleted_at) &&
              `${u.display_name} ${u.email || ""}`.toLowerCase().includes(q),
          ),
        );
      }
      if (p === "/admin/erasure-requests") return clone(this.erasures);
      if (p === "/console/dashboard") {
        const observations = this.store.data.observations.data;
        const validated = observations.filter((o) => o.status === "validated");
        const species = [
          ...new Set(validated.map((o) => o.assignedSpecies).filter(Boolean)),
        ];
        return {
          counts: {
            videos: this.store.data.videos.data.length,
            species: species.length,
            pending: observations.filter((o) => o.status === "review").length,
            tasks: this.tasks.filter((t) =>
              ["queued", "running"].includes(t.status),
            ).length,
          },
          distribution: species.map((label) => ({
            label,
            count: validated.filter((o) => o.assignedSpecies === label).length,
          })),
          latest_training: {
            model_name: "convnext_tiny",
            best_macro_f1: 1,
            run_id: "demo-run-1",
          },
        };
      }
      if (p === "/console/workers")
        return {
          updated_at: date,
          workers: ["vision", "documents"].map((role) => ({
            role,
            online: true,
            running: this.tasks.filter(
              (t) =>
                t.status === "running" &&
                (role === "documents") === t.kind.startsWith("document"),
            ).length,
            queued: this.tasks.filter(
              (t) =>
                t.status === "queued" &&
                (role === "documents") === t.kind.startsWith("document"),
            ).length,
            tasks: this.tasks
              .filter(
                (t) => (role === "documents") === t.kind.startsWith("document"),
              )
              .slice(0, 5)
              .map((t) => ({
                ...t,
                detail: "Simulation locale",
                logs: [
                  {
                    id: 1,
                    message: "Démonstration : aucun worker réel sollicité.",
                    created_at: date,
                  },
                ],
              })),
          })),
        };
      if (p === "/console/videos" || p === "/review/videos") {
        const q = (url.searchParams.get("q") || "").toLowerCase();
        return clone(
          this.videos()
            .filter(
              (v) =>
                (!q || v.filename.toLowerCase().includes(q)) &&
                (!url.searchParams.get("species") ||
                  v.species_candidate === url.searchParams.get("species")) &&
                (!url.searchParams.get("status") ||
                  v.status === url.searchParams.get("status")),
            )
            .slice(offset, offset + limit),
        );
      }
      if ((match = p.match(/^\/console\/videos\/([^/]+)$/))) {
        const video = this.videos().find((v) => v.id === match![1]);
        if (!video) throw new ApiError("Vidéo fictive introuvable", 404);
        return video;
      }
      if (p === "/review/species")
        return this.store.data.species.data.map((s, i) => ({
          name: s.value,
          class_index: i,
          manifest_version: "demo-v1",
        }));
      if (p === "/console/models") return clone(this.models);
      if (p === "/review/datasets")
        return clone(this.datasets.slice(offset, offset + limit));
      if ((match = p.match(/^\/review\/datasets\/([^/]+)$/))) {
        const dataset = this.datasets.find((d) => d.id === match![1]);
        if (!dataset) throw new ApiError("Version fictive introuvable", 404);
        return clone(dataset);
      }
      if (p === "/console/training/datasets")
        return this.datasets.map((d) => {
          const samples = d.manifest?.samples || [];
          const ready =
            samples.some((s) => s.split === "train") &&
            samples.some((s) => s.split === "val");
          return {
            id: d.id,
            name: d.name,
            source: "review",
            ready,
            video_count: new Set(samples.map((s) => s.video_id)).size,
            crop_count: samples.length,
            unavailable_reason: ready
              ? undefined
              : "La simulation nécessite des exemples validés dans les splits train et validation.",
          };
        });
      if (p === "/console/tasks")
        return clone(
          this.tasks
            .filter(
              (t) =>
                !url.searchParams.get("kind") ||
                t.kind === url.searchParams.get("kind"),
            )
            .slice(0, limit),
        );
      if (
        (match = p.match(/^\/(?:console\/tasks|review\/operations)\/([^/]+)$/))
      )
        return clone(this.task(match[1]));
      if ((match = p.match(/^\/console\/tasks\/([^/]+)\/logs$/)))
        return [
          { id: 1, message: "Simulation locale uniquement.", created_at: date },
        ];
      if (p.endsWith("/artifacts/report")) return this.report();
      if (p === "/training/runs")
        return this.tasks
          .filter((t) => t.kind === "training" && t.status === "completed")
          .map((t) => ({
            run_id: t.id,
            status: "completed",
            updated_at: t.finished_at || date,
            metadata: {
              model_name: t.request.model_name,
              best_macro_f1: 1,
              run_id: t.id,
            },
          }));
      if (p.match(/^\/training\/runs\/[^/]+\/metrics$/))
        return [
          {
            event_key: "demo-epoch-1",
            metrics: {
              phase: "head",
              epoch: 1,
              train_loss: 0.12,
              validation: metrics,
            },
          },
        ];
      if (p === "/classification/comparisons")
        return [
          {
            id: "demo-benchmark-1",
            created_at: date,
            dataset_version: "demo-dataset-1",
            human_validated: true,
            protocol: { split: "val" },
            models: this.models.map((model) => ({
              model: { model_id: model.id, classifier_family: "supervised" },
              metrics: clone(metrics),
              coverage: 1,
              failure_rate: 0,
              mean_inference_ms: null,
              error: null,
            })),
          },
        ];
      if (p === "/documents/species")
        return corpusSpecies.map((s) => ({
          name: s.value,
          display_name: s.label,
          scientific_name: "",
          documents_count: this.documents().filter((d) =>
            d.species_links.some((l) => l.species === s.value),
          ).length,
          selected_count: 0,
        }));
      if (p === "/documents")
        return this.documents()
          .filter(
            (d) =>
              !url.searchParams.get("species") ||
              d.species_links.some(
                (l) => l.species === url.searchParams.get("species"),
              ),
          )
          .slice(offset, offset + limit);
      if (p === "/documents/tasks")
        return clone(
          this.tasks
            .filter((t) => t.kind.startsWith("document"))
            .map((t) => ({
              ...t,
              request: { collection_species: t.request.species },
              result: t.status === "completed" ? { downloaded: 1 } : null,
            })),
        );
      if ((match = p.match(/^\/documents\/([^/]+)$/))) {
        const doc = this.documents().find((d) => d.id === match![1]);
        if (!doc) throw new ApiError("Exemple documentaire introuvable", 404);
        return doc;
      }
      if ((match = p.match(/^\/documents\/([^/]+)\/pages$/)))
        return offset
          ? []
          : [
              {
                asset_id: `demo-asset-${match[1]}`,
                page_number: 1,
                clean_text:
                  "EXEMPLE FICTIF — texte de présentation. Aucun article authentique n’est reproduit ni analysé.",
                language: "fr",
              },
            ];
      throw new ApiError(
        "Service non disponible dans ce scénario de démonstration.",
        501,
      );
    }
    if (p === "/admin/users" && method === "POST") {
      if (!String(body.email).endsWith("@example.test"))
        throw new ApiError(
          "Utilisez une adresse fictive en @example.test pour cette démonstration.",
          422,
        );
      const user: User = {
        id: this.id("account"),
        display_name: String(body.display_name),
        email: String(body.email),
        role: body.role === "admin" ? "admin" : "client",
        created_at: date,
        deleted_at: null,
      };
      this.users.push(user);
      return clone(user);
    }
    if (
      (match = p.match(/^\/admin\/users\/([^/]+)(?:\/(role|reset-link))?$/))
    ) {
      const user = this.users.find((u) => u.id === match![1]);
      if (!user) throw new ApiError("Compte fictif introuvable", 404);
      if (match[2] === "role") {
        user.role = body.role === "admin" ? "admin" : "client";
        return clone(user);
      }
      if (match[2] === "reset-link")
        return { path: "/reinitialiser?token=simulation-sans-validite" };
      if (method === "DELETE") {
        user.deleted_at = date;
        user.email = null;
        user.display_name = "Compte fictif supprimé";
        this.erasures.push({
          id: this.id("erasure"),
          user_id: user.id,
          status: "pending",
          requested_at: date,
          note: "",
        });
        return undefined;
      }
    }
    if ((match = p.match(/^\/admin\/erasure-requests\/([^/]+)$/))) {
      const row = this.erasures.find((e) => e.id === match![1]);
      if (!row) throw new ApiError("Demande fictive introuvable", 404);
      row.status = String(body.status);
      row.note = String(body.note);
      return clone(row);
    }
    if (p === "/console/training") {
      const id = this.id("trained-model");
      const operation = this.operation(
        "training",
        body,
        () =>
          this.models.push(
            this.model(id, "Entraînement simulé · checkpoint", false),
          ),
        { model_id: id, metrics },
      );
      this.task(operation.id).pendingResult!.run_id = operation.id;
      return operation;
    }
    if (p === "/console/models") {
      const id = this.id("model");
      return this.operation(
        "register_model",
        body,
        () => this.models.push(this.model(id, String(body.name), false)),
        { model_id: id },
      );
    }
    if ((match = p.match(/^\/console\/models\/([^/]+)\/activate$/))) {
      if (!this.models.some((m) => m.id === match![1]))
        throw new ApiError("Modèle fictif introuvable", 404);
      this.models.forEach((model) => {
        model.active = model.id === match![1];
        model.status = model.active ? "active" : "validated";
      });
      return { active: match[1] };
    }
    if (p.match(/^\/console\/models\/[^/]+\/evaluate$/))
      return this.operation("evaluation", body, undefined, { metrics });
    if (p === "/review/datasets") {
      const id = this.id("dataset"),
        snapshot = this.dataset(id, String(body.name), body);
      return this.operation(
        "dataset",
        body,
        () => this.datasets.unshift(snapshot),
        { dataset_id: id },
      );
    }
    if (p.match(/^\/review\/datasets\/[^/]+\/rebuild$/))
      return this.operation("dataset", body, undefined, {
        dataset_id: p.split("/")[3],
      });
    if ((match = p.match(/^\/console\/tasks\/([^/]+)\/cancel$/))) {
      const task = this.task(match[1]);
      task.status = "cancelled";
      task.cancel_requested = true;
      return { id: task.id, status: "cancelled" };
    }
    if (
      (match = p.match(
        /^\/console\/videos\/([^/]+)\/(analyze|prepare-review)$/,
      ))
    )
      return this.operation(
        match[2] === "analyze" ? "analysis" : "prepare_review",
        { ...body, video_id: match[1] },
        undefined,
        { video_id: match[1], output: "simulation" },
      );
    if (p === "/documents/collect") {
      const ids =
        Array.isArray(body.species) && body.species.length
          ? (body.species as string[])
          : corpusSpecies.map((s) => s.value);
      return ids.map((species) =>
        this.operation("document_collect", { species }, () =>
          this.store.replace("documents", [
            ...this.sharedDocuments(),
            {
              id: this.id("document"),
              species,
              title: `Exemple fictif — ${species} · récupération simulée`,
              kind: "PDF",
              date: "1 novembre 2026",
              origin: "retrieval",
            },
          ]),
        ),
      );
    }
    if (p === "/documents/remove") {
      const ids = new Set(body.documents as string[]);
      this.store.replace(
        "documents",
        this.sharedDocuments().filter(
          (d) => !ids.has(d.id) || d.species !== body.species,
        ),
      );
      return { removed: ids.size };
    }
    if (p === "/documents/upload") {
      const species = url.searchParams.get("species") || "renard";
      const filename = url.searchParams.get("filename") || "";
      return this.operation("document_import", { species }, () =>
        this.store.replace("documents", [
          ...this.sharedDocuments(),
          {
            id: this.id("document"),
            species,
            title: `Import simulé — ${filename}`,
            kind: "PDF",
            date: "1 novembre 2026",
            origin: "import",
            filename,
          },
        ]),
      );
    }
    if (p.match(/^\/documents\/[^/]+\/translate$/))
      return this.operation("document_translate", body);
    if (p === "/console/uploads") {
      const id = this.id("upload");
      this.uploads.set(id, { filename: String(body.filename), approved: true });
      return { id, chunk_size: 4 * 1024 * 1024 };
    }
    if (
      (match = p.match(
        /^\/console\/uploads\/([^/]+)(?:\/(chunks\/\d+|complete))?$/,
      ))
    ) {
      const upload = this.uploads.get(match[1]);
      if (!upload) throw new ApiError("Import fictif introuvable", 404);
      if (match[2] === "complete")
        return this.importVideo(upload.filename, "import_upload");
      if (method === "DELETE") this.uploads.delete(match[1]);
      return undefined;
    }
    if (p === "/console/videos/local")
      return this.importVideo(
        String(body.video_key || "indexation-locale-simulee.mp4")
          .split(/[\\/]/)
          .pop() || "indexation-simulee.mp4",
        "import_local",
      );
    if (p === "/parcels/corpora") {
      const ids = body.video_ids as string[];
      const id = this.id("corpus");
      this.store.replace("projects", [
        ...this.sharedProjects(),
        {
          id,
          name: "Dossier de démonstration",
          videos: ids.length,
          species: new Set(
            this.store.data.videos.data
              .filter((v) => ids.includes(v.id))
              .map((v) => v.species),
          ).size,
          status: "unanalysed",
          project: "forest",
          videoIds: ids,
        },
      ]);
      return { id };
    }
    if (p === "/parcels/import-status")
      return (body.task_ids as string[]).map((id) => clone(this.task(id)));
    throw new ApiError(
      "Action indisponible dans ce scénario. Aucun service réel n’a été appelé.",
      501,
    );
  }
}
