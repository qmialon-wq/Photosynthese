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
let calls: { path: string; options: RequestInit }[], removed: boolean;
const doc = () => ({
  id: "fixture",
  title: "Roads and wildlife",
  authors: [],
  language: "en",
  status: "indexed",
  published_date: null,
  species_links: [],
  assets: [],
  metadata: {
    translation_fr: {
      status: "completed",
      source_title: "Roads and wildlife",
      title: "Routes et faune sauvage",
      abstract: "Résumé en français.",
    },
  },
});
beforeEach(() => {
  calls = [];
  removed = false;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (path: string, options: RequestInit = {}) => {
      calls.push({ path, options });
      let result: unknown = [];
      if (path === "/api/documents/species")
        result = [
          {
            name: "renards",
            display_name: "Renard",
            scientific_name: "Vulpes vulpes",
            documents_count: 1,
          },
          {
            name: "blaireaux",
            display_name: "Blaireau",
            scientific_name: "Meles meles",
            documents_count: 1,
          },
        ];
      else if (path === "/api/documents/fixture") result = doc();
      else if (path.includes("/fixture/pages"))
        result = [
          {
            asset_id: "file",
            page_number: 1,
            clean_text: "English original.",
            translated_text: "Texte français.",
            references_data: [],
          },
        ];
      else if (path.startsWith("/api/documents?"))
        result = removed ? [] : [doc()];
      else if (path === "/api/documents/remove") {
        removed = true;
        result = { removed: ["fixture"] };
      } else if (path === "/api/documents/collect")
        result = { tasks: [{ id: "job" }] };
      return new Response(JSON.stringify(result), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }),
  );
});
afterEach(() => vi.unstubAllGlobals());
describe("corpus simplifié", () => {
  it("masque les notices non téléchargées et lance toutes les espèces en un clic", async () => {
    const wrapper = mount(DocumentsPage, { global });
    await flushPromises();
    expect(calls.some((c) => c.path.includes("stored_only=true"))).toBe(true);
    await wrapper
      .findAll("button")
      .find((b) => b.text() === "Récupérer pour toutes les espèces")!
      .trigger("click");
    await flushPromises();
    expect(
      JSON.parse(
        calls.find((c) => c.path === "/api/documents/collect")!.options
          .body as string,
      ),
    ).toEqual({ species: [] });
    expect(wrapper.text()).not.toContain("Récupérer le texte");
    wrapper.unmount();
  });
  it("collecte des espèces ciblées sans paramètres techniques", async () => {
    const wrapper = mount(DocumentsPage, { global });
    await flushPromises();
    await wrapper
      .findAll("button")
      .find((b) => b.text() === "Choisir les espèces")!
      .trigger("click");
    await wrapper
      .get('.species-choices input[value="blaireaux"]')
      .setValue(true);
    await wrapper.get("form").trigger("submit");
    await flushPromises();
    expect(
      JSON.parse(
        calls.find((c) => c.path === "/api/documents/collect")!.options
          .body as string,
      ),
    ).toEqual({ species: ["renards", "blaireaux"] });
    wrapper.unmount();
  });
  it("affiche le français par défaut et garde un accès à l’original", async () => {
    const wrapper = mount(DocumentsPage, { global });
    await flushPromises();
    expect(wrapper.text()).toContain("Routes et faune sauvage");
    await wrapper
      .findAll("button")
      .find((b) => b.text() === "Lire le document")!
      .trigger("click");
    await flushPromises();
    expect(wrapper.get("pre").text()).toBe("Texte français.");
    await wrapper
      .findAll("button")
      .find((b) => b.text() === "Original")!
      .trigger("click");
    expect(wrapper.get("pre").text()).toBe("English original.");
    wrapper.unmount();
  });
  it("retire une sélection du corpus de l’espèce choisie", async () => {
    const wrapper = mount(DocumentsPage, { global });
    await flushPromises();
    await wrapper.get(".bulk-toolbar input").setValue(true);
    await wrapper
      .findAll("button")
      .find((b) => b.text() === "Retirer du corpus")!
      .trigger("click");
    await flushPromises();
    expect(
      JSON.parse(
        calls.find((c) => c.path === "/api/documents/remove")!.options
          .body as string,
      ),
    ).toEqual({ species: "renards", documents: ["fixture"] });
    expect(wrapper.findAll("article")).toHaveLength(0);
    wrapper.unmount();
  });
  it("refuse les liens actifs des métadonnées", () => {
    expect(externalUrl("javascript:alert(1)")).toBeUndefined();
    expect(externalUrl("https://example.org/article")).toBe(
      "https://example.org/article",
    );
  });
});
