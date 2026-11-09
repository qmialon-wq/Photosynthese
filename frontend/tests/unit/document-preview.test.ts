import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import Pagination from "../../src/components/symbiose/Pagination.vue";
import { afterEach, vi } from "vitest";
import {
  DOCUMENT_PAGE_SIZE_KEY,
  documentPageSize,
  documentPageSizes,
  persistDocumentPageSize,
  restoreDocumentPageSize,
} from "../../src/data/document-page-size";
import {
  demoScientificDocuments,
  documentSpeciesOptions,
  documentsForSpecies,
  importedDocumentKind,
  removePreviewDocuments,
  retrievalExampleDocuments,
} from "../../src/data/document-preview";

describe("corpus documentaire de démonstration", () => {
  afterEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });
  it("dispose de 17 exemples Blaireau identifiés comme fictifs sans modifier les anciens corpus", () => {
    const examples = documentsForSpecies(demoScientificDocuments, "blaireau");
    expect(examples).toHaveLength(17);
    expect(new Set(examples.map((d) => d.id)).size).toBe(17);
    expect(
      examples.every((d) => d.title.startsWith("Exemple fictif") && !d.url),
    ).toBe(true);
  });
  it("restaure uniquement les tailles autorisées et conserve une préférence indépendante", () => {
    localStorage.clear();
    expect(restoreDocumentPageSize()).toBe(16);
    localStorage.setItem("symbiose:videos-per-page:v1", "8");
    for (const size of documentPageSizes) {
      persistDocumentPageSize(size);
      expect(restoreDocumentPageSize()).toBe(size);
    }
    expect(localStorage.getItem("symbiose:videos-per-page:v1")).toBe("8");
    for (const invalid of ["2", "0", "-1", "500", "incorrect", "", null])
      expect(documentPageSize(invalid)).toBe(16);
    localStorage.setItem(DOCUMENT_PAGE_SIZE_KEY, "2");
    expect(restoreDocumentPageSize()).toBe(16);
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    expect(restoreDocumentPageSize()).toBe(16);
    expect(() => persistDocumentPageSize(4)).not.toThrow();
  });
  it("actualise les compteurs et le nombre de pages depuis la même pagination, sans changer ses valeurs par défaut", async () => {
    const wrapper = mount(Pagination, {
      props: {
        variant: "simple",
        showCount: true,
        page: 1,
        total: 50,
        pageSize: 16,
        itemLabel: "document",
      },
    });
    for (const [size, pages] of [
      [4, 13],
      [8, 7],
      [12, 5],
      [16, 4],
    ]) {
      await wrapper.setProps({ pageSize: size, page: 1 });
      expect(wrapper.find("p").text()).toBe(`1 – ${size} sur 50 documents`);
      expect(wrapper.find(".sv-page-current").text()).toBe(
        `Page 1 sur ${pages}`,
      );
    }
    await wrapper.setProps({ total: 0 });
    expect(wrapper.find("p").text()).toBe("0 document");
    expect(
      wrapper
        .findAll("button")
        .every((b) => b.attributes("disabled") !== undefined),
    ).toBe(true);
  });
  it("garde Renard vide et actualise les compteurs depuis les entrées locales", () => {
    expect(documentsForSpecies(demoScientificDocuments, "renard")).toEqual([]);
    expect(documentSpeciesOptions(demoScientificDocuments)[0].label).toBe(
      "Renard · 0 documents",
    );
    const next = [
      ...demoScientificDocuments,
      ...retrievalExampleDocuments(["renard"], 1),
    ];
    expect(documentSpeciesOptions(next)[0].label).toBe("Renard · 1 document");
    expect(
      documentSpeciesOptions(demoScientificDocuments).find(
        (o) => o.value === "chevreuil",
      )?.label,
    ).toBe("Chevreuil · 5 documents");
  });
  it("ne retire que les entrées sélectionnées de la page visible, sans mutation", () => {
    const before = JSON.stringify(demoScientificDocuments);
    const visible = documentsForSpecies(
      demoScientificDocuments,
      "chevreuil",
    ).slice(0, 2);
    const attempted = new Set([
      visible[0].id,
      "example-chevreuil-5",
      "example-blaireau-1",
      "missing",
    ]);
    const result = removePreviewDocuments(
      demoScientificDocuments,
      visible,
      attempted,
    );
    expect(result).toHaveLength(demoScientificDocuments.length - 1);
    expect(
      result.some((document) => document.id === "example-chevreuil-5"),
    ).toBe(true);
    expect(
      result.some((document) => document.id === "example-blaireau-1"),
    ).toBe(true);
    expect(JSON.stringify(demoScientificDocuments)).toBe(before);
  });
  it("accepte uniquement les extensions de démonstration prévues", () => {
    expect(importedDocumentKind("Étude.PDF")).toBe("PDF");
    expect(importedDocumentKind("notes.docx")).toBe("DOCX");
    expect(importedDocumentKind("mes.notes.txt")).toBe("TXT");
    expect(importedDocumentKind("article.pdf.exe")).toBeNull();
    expect(importedDocumentKind("sans-extension")).toBeNull();
  });
  it("produit des exemples explicitement fictifs pour des espèces connues, sans doublons", () => {
    const result = retrievalExampleDocuments(
      ["renard", "renard", "unknown", "blaireau"],
      2,
    );
    expect(result.map((document) => document.species)).toEqual([
      "renard",
      "blaireau",
    ]);
    expect(
      result.every((document) => document.title.startsWith("Exemple fictif")),
    ).toBe(true);
    expect(
      new Set(
        [...result, ...retrievalExampleDocuments(["renard"], 3)].map(
          (document) => document.id,
        ),
      ).size,
    ).toBe(3);
  });
  it("réutilise la pagination simple avec les bornes vides et la dernière page", async () => {
    const wrapper = mount(Pagination, {
      props: {
        variant: "simple",
        page: 1,
        total: 0,
        pageSize: 2,
        navigationLabel: "Pagination du corpus",
      },
    });
    expect(
      wrapper
        .findAll("button")
        .every((button) => button.attributes("disabled") !== undefined),
    ).toBe(true);
    expect(wrapper.find(".sv-page-current").text()).toBe("Page 1");
    await wrapper.setProps({ total: 5, page: 2 });
    await wrapper.findAll("button")[1].trigger("click");
    expect(wrapper.emitted("change")).toEqual([[3]]);
    await wrapper.setProps({ page: 3 });
    expect(wrapper.findAll("button")[1].attributes("disabled")).toBeDefined();
    expect(wrapper.findAll("button")[0].attributes("disabled")).toBeUndefined();
  });
});
