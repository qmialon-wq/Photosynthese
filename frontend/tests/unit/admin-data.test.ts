import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  createDataModeStore,
  type DataModeStore,
} from "../../src/data/data-mode";

import { configureApi, api } from "../../src/api";
import { installAdminServices } from "../../src/admin/services";
import {
  pendingAdminAction,
  closeAdminConfirmation,
} from "../../src/admin/confirmation";
import { acceptSession, clearSession } from "../../src/auth-state";
import { flushPromises } from "@vue/test-utils";
import type { Router } from "vue-router";

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

describe("services administrateur authentifiés", () => {
  it("attend une confirmation avant un POST réel et permet de l’annuler sans envoi", async () => {
    acceptSession(session);
    const data = store();
    data.setActive(false);

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
  it("annule une autorisation en attente si le compte change", async () => {
    acceptSession(session);
    const data = store();
    data.setActive(false);

    installAdminServices(data, router);
    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);
    const operation = api("/console/models", post({ name: "Modèle" }));
    await flushPromises();
    acceptSession({ ...session, user: { ...session.user, id: "next-admin" } });
    await expect(operation).rejects.toThrow("Action annulée");
    expect(fetch).not.toHaveBeenCalled();
  });
});

it("consulte le suivi groupé des imports sans demander une nouvelle confirmation", async () => {
  acceptSession(session);
  const data = store();
  data.setActive(false);

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
  acceptSession({ ...session, user: { ...session.user, id: "next-admin" } });
  respond(
    new Response(JSON.stringify({ detail: "Ancienne session expirée" }), {
      status: 401,
    }),
  );
  await expect(request).rejects.toThrow("Source changée");
  const { auth } = await import("../../src/auth-state");
  expect(auth.user?.id).toBe("next-admin");
});
