import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  createDataModeStore,
  DATA_MODE_KEY,
  type DataModeStore,
} from "../../src/data/data-mode";
import { createDemoSnapshot, summarize } from "../../src/data/demo-provider";
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

describe("scénario central de démonstration", () => {
  it("lie les pages par identifiants et calcule leurs compteurs", () => {
    const data = createDemoSnapshot();
    expect(data.videos.data).toHaveLength(248);
    expect(data.projects.data).toHaveLength(12);
    expect(data.observations.data).toHaveLength(8);
    expect(
      data.projects.data.reduce((total, p) => total + (p.videos || 0), 0),
    ).toBe(248);
    for (const project of data.projects.data) {
      const members = data.videos.data.filter(
        (v) => v.projectId === project.id,
      );
      expect(project.videoIds).toEqual(members.map((v) => v.id));
      expect(project.species).toBe(new Set(members.map((v) => v.species)).size);
    }
    for (const analysis of data.analyses.data) {
      const related = data.videos.data.find((v) => v.id === analysis.videoId)!;
      expect(analysis.filename).toBe(related.filename);
      expect(analysis.duration).toBe(related.durationSeconds);
    }
    for (const observation of data.observations.data) {
      expect(observation.filename).toBe(
        data.videos.data.find((v) => v.id === observation.videoId)?.filename,
      );
    }
    const home = summarize(data, true);
    expect(home.overview.map((s) => s.value)).toEqual(["12", "8", "2", "4"]);
    expect(home.videoOverview[2].value).toBe(home.overview[0].value);
  });
  it("produit un nouvel état sans modifier les fixtures lors d’une simulation", () => {
    const first = createDemoSnapshot(),
      second = createDemoSnapshot();
    first.documents.data.splice(0, 1);
    first.observations.data[0].status = "review";
    expect(second.documents.data).toHaveLength(24);
    expect(second.observations.data[0].status).toBe("validated");
  });
});

describe("source réelle en lecture seule", () => {
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
    expect(summarize(data, false).videoOverview[1].value).toBe("6,8 s");
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
    expect(summarize(data, false).score).toBeNull();
    expect(summarize(data, false).recommendations).toEqual([]);
    expect(summarize(data, false).videoOverview[1].value).toBe("—");
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
    expect(summarize(data, false).overview[1].value).toBe("—");
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
    expect(summarize(data, false).videoOverview[0].value).toBe("201");
  });
});

describe("contexte global et séparation des modes", () => {
  it("démarre en démonstration, persiste le choix et tolère un stockage refusé", async () => {
    const store = createDataModeStore();
    stores.push(store);
    expect(store.mode.value).toBe("demo");
    store.setMode("real");
    expect(localStorage.getItem(DATA_MODE_KEY)).toBe("real");
    const restored = createDataModeStore();
    stores.push(restored);
    expect(restored.isReal.value).toBe(true);
    const unavailable = createDataModeStore({
      getItem() {
        throw new Error();
      },
      setItem() {
        throw new Error();
      },
    });
    stores.push(unavailable);
    expect(unavailable.isDemo.value).toBe(true);
    expect(() => unavailable.setMode("real")).not.toThrow();
  });
  it("ignore une réponse tardive et refuse toute mutation simulée en réel", async () => {
    let publish!: Parameters<DataProvider["load"]>[1];
    let release!: () => void;
    let signal!: AbortSignal;
    const real: DataProvider = {
      id: "real:test",
      async load(current, callback) {
        signal = current;
        publish = callback;
        await new Promise<void>((resolve) => {
          release = resolve;
        });
      },
    };
    const demo: DataProvider = {
      id: "demo:test",
      async load(_, callback) {
        callback(
          "videos",
          resource([{ ...adaptVideo(video), id: "demo-only" }]),
        );
      },
    };
    const store = createDataModeStore(undefined, { real, demo });
    stores.push(store);
    store.setActive(true);
    store.setMode("real");
    expect(store.data.videos.data).toEqual([]);
    store.replace("videos", [{ ...adaptVideo(video), id: "forbidden" }]);
    const action = vi.fn();
    store.simulate(action);
    expect(action).not.toHaveBeenCalled();
    store.setMode("demo");
    expect(signal.aborted).toBe(true);
    publish("videos", resource([adaptVideo(video)]));
    release();
    await flushPromises();
    expect(store.data.videos.data.map((v) => v.id)).toEqual(["demo-only"]);
  });
  it("ne lit rien sur Connexion et invalide les données lors d’un changement de compte", async () => {
    auth.user = session.user;
    let loads = 0;
    const real: DataProvider = {
      id: "real:test",
      async load(_, publish) {
        loads++;
        publish("videos", resource([adaptVideo(video)]));
      },
    };
    const store = createDataModeStore(undefined, { demo: real, real });
    stores.push(store);
    store.setMode("real");
    expect(loads).toBe(0);
    store.setActive(true);
    const revision = store.revision.value;
    auth.user = { ...session.user, id: "account-b" };
    expect(store.revision.value).toBeGreaterThan(revision);
    expect(store.sourceId.value).toContain("account-b");
    expect(loads).toBe(2);
  });
});
