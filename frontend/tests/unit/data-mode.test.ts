import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  createDataModeStore,
  DATA_MODE_KEY,
  type DataModeStore,
} from "../../src/data/data-mode";
import { summarize } from "../../src/data/summary";
import { RealDataProvider, adaptVideo } from "../../src/data/real-provider";
import {
  emptySnapshot,
  resource,
  type DataProvider,
  type Snapshot,
} from "../../src/data/contracts";
import { ApiError } from "../../src/api";
import { auth, clearSession, type Session } from "../../src/auth-state";
import { flushPromises } from "@vue/test-utils";

const stores: DataModeStore[] = [];
const session: Session = {
  user: {
    id: "account-a",
    display_name: "Camille",
    email: null,
    role: "client",
    created_at: "2026-01-01",
    deleted_at: null,
  },
  csrf_token: "test",
};
const video = {
  id: "real-video",
  filename: "terrain.mp4",
  species_candidate: null,
  status: "ready",
  created_at: "2026-11-01",
  metadata: {},
};
beforeEach(() => {
  localStorage.clear();
  clearSession();
});
afterEach(() => {
  stores.splice(0).forEach((store) => store.dispose());
  vi.restoreAllMocks();
});
async function read(provider: DataProvider) {
  const result = emptySnapshot();
  await provider.load(new AbortController().signal, (key, value) =>
    Object.assign(result, { [key]: value }),
  );
  return result;
}
function transport(overrides: Record<string, unknown> = {}) {
  return vi.fn(async (path: string, options?: RequestInit) => {
    expect(options?.method).toBe("GET");
    const url = new URL(path, "https://symbiose.test");
    const value =
      overrides[url.pathname] ?? (url.pathname === "/auth/me" ? session : []);
    if (value instanceof Error) throw value;
    return value;
  }) as unknown as ConstructorParameters<typeof RealDataProvider>[0] &
    ReturnType<typeof vi.fn>;
}

describe("contexte authentifié sans démonstration", () => {
  it("ignore l'ancien mode démo enregistré et ne charge rien sans session", () => {
    localStorage.setItem(DATA_MODE_KEY, "demo");
    const load = vi.fn();
    const store = createDataModeStore(localStorage, { id: "real:test", load });
    stores.push(store);
    store.setActive(true);
    expect(localStorage.getItem(DATA_MODE_KEY)).toBe("real");
    expect(store.capabilities.value.write).toBe(false);
    expect(load).not.toHaveBeenCalled();
  });

  it("active les écritures client et admin et efface les données à la déconnexion", () => {
    const provider: DataProvider = {
      id: "real:test",
      async load(_, publish) {
        publish("videos", resource([adaptVideo(video)]));
      },
    };
    const store = createDataModeStore(undefined, provider);
    stores.push(store);
    store.setActive(true);
    auth.user = session.user;
    expect(store.capabilities.value.write).toBe(true);
    expect(store.capabilities.value.readOnly).toBe(false);
    expect(store.data.videos.data).toHaveLength(1);
    auth.user = { ...session.user, role: "admin" };
    expect(store.capabilities.value.write).toBe(true);
    clearSession();
    expect(store.data.videos.data).toEqual([]);
    expect(store.capabilities.value.write).toBe(false);
  });

  it("annule le chargement précédent après un changement de compte", async () => {
    auth.user = session.user;
    const pending: {
      signal: AbortSignal;
      publish: Parameters<DataProvider["load"]>[1];
      finish: () => void;
    }[] = [];
    const provider: DataProvider = {
      id: "real:test",
      load: (signal, publish) =>
        new Promise<void>((finish) =>
          pending.push({ signal, publish, finish }),
        ),
    };
    const store = createDataModeStore(undefined, provider);
    stores.push(store);
    store.setActive(true);
    auth.user = { ...session.user, id: "account-b" };
    expect(pending[0].signal.aborted).toBe(true);
    pending[0].publish("videos", resource([adaptVideo(video)]));
    pending[0].finish();
    await flushPromises();
    expect(store.data.videos.data).toEqual([]);
    expect(store.sourceId.value).toContain("account-b");
    pending[1].publish(
      "videos",
      resource([{ ...adaptVideo(video), id: "account-b-video" }]),
    );
    pending[1].finish();
    await flushPromises();
    expect(store.data.videos.data[0].id).toBe("account-b-video");
  });
});

describe("source réelle", () => {
  it("choisit la première vidéo dans l'ordre du dossier, indépendamment de la vidéothèque", async () => {
    const data = await read(
      new RealDataProvider(
        transport({
          "/console/videos": [
            { ...video, id: "second", metadata: { poster_url: "/second.jpg" } },
            { ...video, id: "first", metadata: { poster_url: "/first.jpg" } },
          ],
          "/parcels/corpora": [{ id: "ordered" }, { id: "empty" }],
          "/parcels/corpora/ordered": {
            videos: [
              { video_id: "first", filename: "premiere.mp4" },
              { video_id: "second", filename: "seconde.mp4" },
            ],
            profile: null,
            dossier: null,
          },
          "/parcels/corpora/empty": {
            videos: [],
            profile: null,
            dossier: null,
          },
        }),
      ),
    );
    expect(data.projects.data[0].previewVideo).toEqual({
      id: "first",
      filename: "premiere.mp4",
      source: "/api/console/videos/first/file",
      poster: "/first.jpg",
    });
    expect(data.projects.data[1].previewVideo).toBeUndefined();
  });

  it("conserve la première vidéo même lorsque les métadonnées de la vidéothèque sont indisponibles", async () => {
    const data = await read(
      new RealDataProvider(
        transport({
          "/console/videos": new ApiError("Indisponible", 503),
          "/parcels/corpora": [{ id: "corpus" }],
          "/parcels/corpora/corpus": {
            videos: [{ video_id: "first", filename: "premiere.mp4" }],
            profile: null,
            dossier: null,
          },
        }),
      ),
    );
    expect(data.projects.state).toBe("success");
    expect(data.projects.data[0].previewVideo).toMatchObject({
      id: "first",
      source: "/api/console/videos/first/file",
    });
  });

  it("affiche uniquement les actions des dossiers terminés et conserve le lien vers leur parcelle", async () => {
    const action = {
      title: "Conserver la haie existante",
      action: "Maintenir la continuité de la haie.",
      priority: "design",
    };
    const data = await read(
      new RealDataProvider(
        transport({
          "/parcels/corpora": [{ id: "completed" }, { id: "running" }],
          "/parcels/corpora/completed": {
            videos: [],
            profile: null,
            dossier: {
              status: "completed",
              result: {
                territorial_report: { status: "generated", actions: [action] },
              },
            },
          },
          "/parcels/corpora/running": {
            videos: [],
            profile: null,
            dossier: {
              status: "running",
              result: {
                territorial_report: { status: "generated", actions: [action] },
              },
            },
          },
        }),
      ),
    );
    const summary = summarize(data);
    expect(summary.score).toBeNull();
    expect(summary.recommendations).toEqual([
      {
        id: "completed-action-0",
        title: action.title,
        description: action.action,
        priority: "design",
        projectId: "completed",
      },
    ]);
    expect(summary.overview[3].value).toBe("1");
  });
  it("relie les dossiers aux vidéos et conserve les durées courtes réelles", async () => {
    const data = await read(
      new RealDataProvider(
        transport({
          "/console/videos": [
            { ...video, metadata: { duration_seconds: 6.8 } },
          ],
          "/parcels/corpora": [{ id: "corpus", video_count: 1 }],
          "/parcels/corpora/corpus": {
            videos: [{ video_id: video.id }],
            profile: { profile: { locality: "Lieu enregistré" } },
            dossier: null,
          },
        }),
      ),
    );
    expect(data.videos.data[0].parcel).toBe("Lieu enregistré");
    expect(data.videos.data[0].projectId).toBe("corpus");
    expect(summarize(data).videoOverview[1].value).toBe("6,8 s");
    expect(data.projects.data[0].species).toBe(0);
  });
  it("contrôle la session avant les données et ne transforme pas les absences en valeurs fictives", async () => {
    const request = transport({ "/console/videos": [video] });
    const data = await read(new RealDataProvider(request));
    expect(request.mock.calls[0][0]).toBe("/auth/me");
    expect(data.videos.state).toBe("success");
    expect(data.videos.data[0]).toMatchObject({
      filename: "terrain.mp4",
      species: "",
      duration: "",
      status: "ready",
    });
    expect(data.videos.data[0].thumbnail).toBeUndefined();
    expect(data.videos.data[0].durationSeconds).toBeUndefined();
    expect(summarize(data).score).toBeNull();
    expect(summarize(data).recommendations).toEqual([]);
    expect(summarize(data).videoOverview[1].value).toBe("—");
  });
  it("ne charge aucune donnée métier si la session est absente", async () => {
    const request = transport({
      "/auth/me": new ApiError("Session absente", 401),
    });
    const data = await read(new RealDataProvider(request));
    expect(request).toHaveBeenCalledTimes(1);
    expect(data.videos.state).toBe("error");
    expect(data.videos.message).toContain("Connexion requise");
    expect(data.videos.data).toEqual([]);
  });
  it("distingue source non connectée, erreur et résultat vide sans repli sur la démonstration", async () => {
    const request = transport({
      "/console/videos": new ApiError("Absente", 503),
      "/review/samples": new ApiError("Interdit", 403),
    });
    const data = await read(new RealDataProvider(request));
    expect(data.videos.state).toBe("unconnected");
    expect(data.observations.state).toBe("error");
    expect(data.documents.state).toBe("empty");
    expect(summarize(data).overview[1].value).toBe("—");
    expect(
      Object.values(data).every((source) => source.data.length === 0),
    ).toBe(true);
  });
  it("refuse une réponse invalide au lieu d’afficher un faux succès", async () => {
    const data = await read(
      new RealDataProvider(
        transport({ "/console/videos": { videos: [video] } }),
      ),
    );
    expect(data.videos.state).toBe("error");
    expect(data.videos.data).toEqual([]);
  });
  it("parcourt les pages de l’API avant de calculer un total", async () => {
    const request = transport();
    request.mockImplementation(async (path: string) => {
      if (path === "/auth/me") return session;
      if (path.startsWith("/console/videos")) {
        const offset = Number(
          new URL(path, "https://test").searchParams.get("offset"),
        );
        return Array.from({ length: offset === 0 ? 200 : 1 }, (_, i) => ({
          ...video,
          id: `real-${offset + i}`,
        }));
      }
      return [];
    });
    const data = await read(new RealDataProvider(request));
    expect(data.videos.data).toHaveLength(201);
    expect(summarize(data).videoOverview[0].value).toBe("201");
  });
});
