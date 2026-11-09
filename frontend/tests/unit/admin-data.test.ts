import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  createDataModeStore,
  type DataModeStore,
} from "../../src/data/data-mode";
import { AdminDemoProvider } from "../../src/admin/demo-provider";
import { configureApi, api } from "../../src/api";
import { installAdminServices } from "../../src/admin/services";
import {
  pendingAdminAction,
  closeAdminConfirmation,
} from "../../src/admin/confirmation";
import { acceptSession, clearSession } from "../../src/auth-state";
import { flushPromises } from "@vue/test-utils";
import type { Router } from "vue-router";
import type { Dataset, Model } from "../../src/types";
const stores: DataModeStore[] = [];
const session = {
  user: {
    id: "server-admin",
    display_name: "Admin de test",
    role: "admin" as const,
    email: null,
    created_at: "2026-11-01",
    deleted_at: null,
  },
  csrf_token: "test-csrf",
};
function store() {
  const value = createDataModeStore();
  stores.push(value);
  value.setActive(true);
  return value;
}
const router = {
  currentRoute: { value: { path: "/admin/training" } },
} as unknown as Router;
beforeEach(() => {
  localStorage.clear();
  clearSession();
});
afterEach(() => {
  closeAdminConfirmation();
  configureApi();
  stores.splice(0).forEach((s) => s.dispose());
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});
const post = (body: unknown) => ({
  method: "POST",
  body: JSON.stringify(body),
});

describe("adaptateur administrateur de démonstration", () => {
  it("alimente le dashboard depuis le scénario commun et utilise uniquement des comptes fictifs", async () => {
    const data = store(),
      provider = new AdminDemoProvider(data);
    const dashboard = (await provider.request("/console/dashboard")) as {
      counts: { videos: number; species: number; pending: number };
    };
    expect(dashboard.counts).toMatchObject({
      videos: 248,
      species: 2,
      pending: 6,
    });
    const accounts = (await provider.request("/admin/users")) as {
      email: string | null;
    }[];
    expect(
      accounts.every((a) => !a.email || a.email.endsWith("@example.test")),
    ).toBe(true);
  });
  it("modifie uniquement les comptes locaux et conserve la séparation entre les deux sources", async () => {
    const data = store(),
      provider = new AdminDemoProvider(data);
    const created = (await provider.request(
      "/admin/users",
      post({
        email: "demo@example.test",
        display_name: "Compte fictif",
        password: "mot-de-passe-fictif",
        role: "client",
      }),
    )) as { id: string };
    expect(created.id).toMatch(/^demo-/);
    await provider.request(`/admin/users/${created.id}`, { method: "DELETE" });
    expect(
      ((await provider.request("/admin/erasure-requests")) as unknown[]).length,
    ).toBe(2);
    expect(
      (
        (await provider.request(
          "/admin/users?q=Compte%20fictif&include_deleted=false",
        )) as unknown[]
      ).length,
    ).toBe(0);
  });
  it("conserve une version de dataset immuable et garde chaque groupe dans un seul split", async () => {
    const data = store();
    data.replace(
      "observations",
      data.data.observations.data.map((o) => ({
        ...o,
        assignedSpecies: "renard",
        status: "validated",
        media: { ...o.media, detections: [...o.media.detections] },
      })),
    );
    const provider = new AdminDemoProvider(data);
    const before = (await provider.request(
      "/review/datasets/demo-dataset-1",
    )) as Dataset;
    const splits = new Map<string, Set<string>>();
    before.manifest!.samples.forEach((sample) => {
      if (!splits.has(sample.video_id)) splits.set(sample.video_id, new Set());
      splits.get(sample.video_id)!.add(sample.split);
    });
    expect([...splits.values()].every((s) => s.size === 1)).toBe(true);
    data.replace("observations", []);
    expect(await provider.request("/review/datasets/demo-dataset-1")).toEqual(
      before,
    );
  });
  it("simule la progression et enregistre un checkpoint sans l’activer", async () => {
    let clock = 1000;
    const provider = new AdminDemoProvider(store(), () => clock);
    const operation = (await provider.request(
      "/console/training",
      post({ dataset_id: "demo-dataset-1", model_name: "convnext_tiny" }),
    )) as { id: string };
    expect(
      await provider.request(`/console/tasks/${operation.id}`),
    ).toMatchObject({ status: "queued", result: null });
    clock += 1200;
    expect(
      await provider.request(`/console/tasks/${operation.id}`),
    ).toMatchObject({ status: "running" });
    clock += 1500;
    expect(
      await provider.request(`/console/tasks/${operation.id}`),
    ).toMatchObject({ status: "completed" });
    const models = (await provider.request("/console/models")) as Model[];
    expect(models).toHaveLength(3);
    expect(models.filter((m) => m.active)).toHaveLength(1);
    expect(models.at(-1)?.active).toBe(false);
  });
  it("partage le même corpus que les pages d’observation", async () => {
    let clock = 0;
    const data = store(),
      provider = new AdminDemoProvider(data, () => clock);
    await provider.request("/documents/collect", post({ species: ["renard"] }));
    clock = 3000;
    await provider.request("/documents/tasks");
    expect(
      data.data.documents.data.filter((d) => d.species === "renard"),
    ).toHaveLength(1);
    const doc = data.data.documents.data.find((d) => d.species === "renard")!;
    await provider.request(
      "/documents/remove",
      post({ species: "renard", documents: [doc.id] }),
    );
    expect(
      data.data.documents.data.filter((d) => d.species === "renard"),
    ).toHaveLength(0);
  });
});

describe("politique de transport et confirmations", () => {
  it("ne fait jamais appel au réseau pour une opération administrative de démonstration", async () => {
    acceptSession(session);
    const data = store();
    installAdminServices(data, router);
    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);
    await api(
      "/admin/users",
      post({
        email: "nouveau@example.test",
        display_name: "Fictif",
        password: "simulation",
        role: "client",
      }),
    );
    expect(fetch).not.toHaveBeenCalled();
    await expect(api("/non-connecte")).rejects.toThrow(
      "Service non disponible",
    );
    expect(fetch).not.toHaveBeenCalled();
  });
  it("attend une confirmation avant un POST réel et permet de l’annuler sans envoi", async () => {
    acceptSession(session);
    const data = store();
    data.setActive(false);
    data.setMode("real");
    installAdminServices(data, router);
    const fetch = vi.fn(
      async () =>
        new Response(JSON.stringify({ id: "real-operation" }), {
          headers: { "Content-Type": "application/json" },
        }),
    );
    vi.stubGlobal("fetch", fetch);
    const operation = api("/console/training", post({ dataset_id: "real-id" }));
    await flushPromises();
    expect(pendingAdminAction.value).not.toBeNull();
    expect(fetch).not.toHaveBeenCalled();
    pendingAdminAction.value!.finish(false);
    await expect(operation).rejects.toThrow("Action annulée");
    expect(fetch).not.toHaveBeenCalled();
    const next = api("/console/training", post({ dataset_id: "real-id" }));
    await flushPromises();
    pendingAdminAction.value!.finish(true);
    expect(await next).toEqual({ id: "real-operation" });
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch.mock.calls[0][1].headers.get("X-CSRF-Token")).toBe(
      "test-csrf",
    );
  });
  it("annule une autorisation en attente si le mode change", async () => {
    acceptSession(session);
    const data = store();
    data.setActive(false);
    data.setMode("real");
    installAdminServices(data, router);
    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);
    const operation = api("/console/models", post({ name: "Modèle" }));
    await flushPromises();
    data.setMode("demo");
    await expect(operation).rejects.toThrow("Action annulée");
    expect(fetch).not.toHaveBeenCalled();
  });
});

it("indexe un nom de fichier uniquement dans la vidéothèque de démonstration", async () => {
  let clock = 0;
  const data = store(),
    provider = new AdminDemoProvider(data, () => clock);
  const upload = (await provider.request(
    "/console/uploads",
    post({ filename: "capture-locale.mp4" }),
  )) as { id: string };
  const operation = (await provider.request(
    `/console/uploads/${upload.id}/complete`,
    post({}),
  )) as { id: string };
  clock = 3000;
  await provider.request(`/console/tasks/${operation.id}`);
  expect(data.data.videos.data).toHaveLength(249);
  expect(data.data.videos.data[0]).toMatchObject({
    filename: "capture-locale.mp4",
    species: "Non déterminée",
  });
});
it("consulte le suivi groupé des imports sans demander une nouvelle confirmation", async () => {
  acceptSession(session);
  const data = store();
  data.setActive(false);
  data.setMode("real");
  installAdminServices(data, router);
  const fetch = vi.fn(
    async () =>
      new Response("[]", { headers: { "Content-Type": "application/json" } }),
  );
  vi.stubGlobal("fetch", fetch);
  await expect(
    api("/parcels/import-status", post({ task_ids: ["server-id"] })),
  ).resolves.toEqual([]);
  expect(pendingAdminAction.value).toBeNull();
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("ignore une erreur 401 tardive d’une ancienne source sans fermer la session actuelle", async () => {
  acceptSession(session);
  const data = store();
  data.setActive(false);
  data.setMode("real");
  installAdminServices(data, router);
  let respond!: (response: Response) => void;
  vi.stubGlobal(
    "fetch",
    vi.fn(
      () =>
        new Promise<Response>((resolve) => {
          respond = resolve;
        }),
    ),
  );
  const request = api("/console/models");
  await flushPromises();
  data.setMode("demo");
  respond(
    new Response(JSON.stringify({ detail: "Ancienne session expirée" }), {
      status: 401,
    }),
  );
  await expect(request).rejects.toThrow("Source changée");
  const { auth } = await import("../../src/auth-state");
  expect(auth.user?.id).toBe("server-admin");
});
