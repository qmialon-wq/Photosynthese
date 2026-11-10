import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import TerritorialContext from "../../src/components/TerritorialContext.vue";
import ParcelCorpusPage from "../../src/pages/ParcelCorpusPage.vue";
import LoadState from "../../src/components/LoadState.vue";
import { acceptSession, auth, clearSession } from "../../src/auth-state";
import { configureApi } from "../../src/api";
import {
  createDataModeStore,
  dataModeKey,
  type DataModeStore,
} from "../../src/data/data-mode";
import { installAdminServices } from "../../src/admin/services";
let store: DataModeStore;
const disposals: Array<() => void> = [];
const profile = {
  area_m2: 2500,
  land_type: "pasture",
  project_type: "housing",
  details: "Conserver",
  locality: "Caen",
};
const state = () => ({
  location: null,
  profile,
  profile_revision: 4,
  query: null,
});
beforeEach(() => {
  clearSession();
  configureApi();
  acceptSession({
    user: {
      id: "owner",
      role: "client",
      email: null,
      display_name: "Test",
      created_at: "2026-11-10",
      deleted_at: null,
    },
    csrf_token: "csrf-test",
  });
  store = createDataModeStore({ getItem: () => "real", setItem: () => {} });
});
afterEach(() => {
  disposals.splice(0).forEach((fn) => fn());
  store.dispose();
  configureApi();
  vi.unstubAllGlobals();
});
function render(owner = "owner") {
  const wrapper = mount(TerritorialContext, {
    props: { corpusId: "corpus", owner },
    global: {
      provide: { [dataModeKey as symbol]: store },
      stubs: { TerritorialPointMap: true },
    },
  });
  disposals.push(() => wrapper.unmount());
  return wrapper;
}
it("enregistre uniquement les interventions, avec CSRF et révision", async () => {
  const calls: Array<{ url: string; options: RequestInit }> = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, options: RequestInit) => {
      calls.push({ url, options });
      return new Response(JSON.stringify(state()));
    }),
  );
  const wrapper = render();
  await flushPromises();
  expect(wrapper.text()).toContain("profil historique");
  await wrapper.get('input[value="fencing"]').setValue(true);
  await wrapper.findAll("form")[1].trigger("submit");
  await flushPromises();
  const request = calls.find((c) => c.options.method === "PUT")!;
  expect(request.url).toBe("/api/parcels/corpora/corpus/profile");
  expect(JSON.parse(request.options.body as string)).toEqual({
    interventions: ["fencing"],
    expected_revision: 4,
  });
  expect(new Headers(request.options.headers).get("X-CSRF-Token")).toBe(
    "csrf-test",
  );
});
it("refuse l’édition d’un autre propriétaire et ne consulte rien en démonstration", async () => {
  const fetch = vi.fn(async () => new Response(JSON.stringify(state())));
  vi.stubGlobal("fetch", fetch);
  const wrapper = render("other");
  await flushPromises();
  expect(wrapper.find('button[type="submit"]').exists()).toBe(false);
  wrapper.unmount();
  store.setMode("demo");
  fetch.mockClear();
  const demo = render();
  await flushPromises();
  expect(fetch).not.toHaveBeenCalled();
  expect(demo.text()).toContain("aucune consultation territoriale réelle");
});
it("garde les formulaires historiques en lecture seule pour le propriétaire", async () => {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/parcelles/:id", component: ParcelCorpusPage }],
  });
  await router.push("/parcelles/corpus");
  await router.isReady();
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async (url: string) =>
        new Response(
          JSON.stringify(
            url.includes("territorial-context")
              ? state()
              : url.endsWith("/options")
                ? { land_types: {}, project_types: {} }
                : {
                    id: "corpus",
                    actor: "owner",
                    videos: [],
                    profile: { revision: 4, profile },
                    dossier: null,
                  },
          ),
        ),
    ),
  );
  const wrapper = mount(ParcelCorpusPage, {
    props: { readOnly: true },
    global: {
      plugins: [router],
      components: { LoadState },
      provide: { [dataModeKey as symbol]: store },
      stubs: { TerritorialPointMap: true },
    },
  });
  disposals.push(() => wrapper.unmount());
  await flushPromises();
  expect(wrapper.find('input[value="fencing"]').exists()).toBe(true);
  expect(wrapper.find('input[max="1000000000"]').exists()).toBe(false);
  expect(wrapper.text()).toContain("2500 m²");
});
it("invalide une réponse tardive après un changement de compte ou de mode", async () => {
  const router = {
    currentRoute: { value: { path: "/parcelles/corpus" } },
  } as unknown as Parameters<typeof installAdminServices>[1];
  installAdminServices(store, router);
  let resolve: (value: Response) => void = () => {};
  vi.stubGlobal(
    "fetch",
    vi.fn(
      () =>
        new Promise<Response>((done) => {
          resolve = done;
        }),
    ),
  );
  const wrapper = render();
  await flushPromises();
  auth.user = { ...auth.user!, id: "another" };
  store.setMode("demo");
  resolve(
    new Response(
      JSON.stringify({
        ...state(),
        profile: { ...profile, locality: "RÉPONSE PÉRIMÉE" },
      }),
    ),
  );
  await flushPromises();
  expect(wrapper.text()).not.toContain("RÉPONSE PÉRIMÉE");
  expect(wrapper.text()).toContain("Mode démonstration");
});
