import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import PrimeVue from "primevue/config";
import Button from "primevue/button";
import DocumentsPage from "../../src/pages/DocumentsPage.vue";
import LoadState from "../../src/components/LoadState.vue";
import { externalUrl } from "../../src/documents";

const global = {
  plugins: [PrimeVue],
  components: { PButton: Button, LoadState },
  stubs: {
    PDialog: {
      props: ["visible"],
      template: '<section v-if="visible"><slot /></section>',
    },
  },
};
let selected = false;
let calls: { path: string; options: RequestInit }[];
function document() {
  return {
    id: "fixture",
    title: "Étude de test sur le renard",
    authors: ["Auteur de test"],
    status: "indexed",
    abstract: "Résumé de test",
    published_date: "2026",
    doi: null,
    url: "https://example.org/fixture",
    species_links: [
      { species: "renards", enabled: selected, available: selected },
    ],
    assets: [],
    provenance: [],
    selection_history: [],
  };
}
beforeEach(() => {
  selected = false;
  calls = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (path: string, options: RequestInit = {}) => {
      calls.push({ path, options });
      let result: unknown = [];
      if (path === "/api/documents/search-profiles")
        result = {
          version: "test",
          activities: [
            { value: "all", label: "Tous les aménagements" },
            { value: "transport", label: "Routes et transports" },
          ],
        };
      else if (path.endsWith("/species/renards")) {
        selected = JSON.parse(options.body as string).enabled;
        result = {};
      } else if (path === "/api/documents/species")
        result = [
          {
            name: "renards",
            scientific_name: "Vulpes vulpes",
            display_name: "Renard",
            documents_count: 1,
            selected_count: Number(selected),
          },
        ];
      else if (path === "/api/documents/fixture") result = document();
      else if (path.includes("/fixture/pages"))
        result = [
          {
            asset_id: "fixture",
            page_number: 1,
            clean_text: "Texte extrait de test.",
            language: "fr",
            references_data: [],
          },
        ];
      else if (path.startsWith("/api/documents?")) result = [document()];
      else if (
        path === "/api/documents/search" ||
        path.startsWith("/api/documents/upload")
      )
        result = { id: "job" };
      else if (path === "/api/documents/tasks/job")
        result = { id: "job", status: "queued" };
      return new Response(JSON.stringify(result), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }),
  );
});
afterEach(() => vi.unstubAllGlobals());

describe("bibliothèque documentaire", () => {
  it("lance une recherche par nom scientifique sans ajouter automatiquement les sources", async () => {
    const wrapper = mount(DocumentsPage, { global });
    await flushPromises();
    await wrapper.get('input[type="checkbox"]').setValue(true);
    await flushPromises();
    await wrapper
      .findAll("button")
      .find((b) => b.text() === "Rechercher des publications")!
      .trigger("click");
    await wrapper.get("form").trigger("submit");
    await flushPromises();
    const call = calls.find((c) => c.path === "/api/documents/search")!;
    expect(JSON.parse(call.options.body as string)).toMatchObject({
      species: ["Vulpes vulpes"],
      download_fulltext: true,
      focus: "human_activities",
      activity: "all",
    });
    expect(calls.some((c) => c.options.method === "PUT")).toBe(false);
    expect(wrapper.text()).toContain("Recherche lancée");
    expect(
      (wrapper.get('input[type="checkbox"]').element as HTMLInputElement)
        .checked,
    ).toBe(false);
    wrapper.unmount();
  });
  it("consulte le texte puis ajoute et retire une source par espèce", async () => {
    const wrapper = mount(DocumentsPage, { global });
    await flushPromises();
    await wrapper
      .findAll("button")
      .find((b) => b.text() === "Consulter")!
      .trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("Texte extrait de test.");
    await wrapper
      .findAll("button")
      .find((b) => b.text() === "Valider et ajouter aux sources")!
      .trigger("click");
    await flushPromises();
    expect(selected).toBe(true);
    await wrapper
      .findAll("button")
      .find((b) => b.text() === "Retirer des sources")!
      .trigger("click");
    await flushPromises();
    expect(selected).toBe(false);
    expect(
      calls
        .filter((c) => c.options.method === "PUT")
        .map((c) => JSON.parse(c.options.body as string)),
    ).toEqual([{ enabled: true }, { enabled: false }]);
    wrapper.unmount();
  });
  it("refuse les liens actifs provenant de métadonnées non fiables", () => {
    expect(externalUrl("javascript:alert(1)")).toBeUndefined();
    expect(externalUrl("data:text/html,fixture")).toBeUndefined();
    expect(externalUrl("https://example.org/article")).toBe(
      "https://example.org/article",
    );
  });
});
