import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import Pagination from "../../src/components/symbiose/Pagination.vue";
import {
  demoScientificDocuments,
  documentSpeciesOptions,
  documentsForSpecies,
  importedDocumentKind,
  removePreviewDocuments,
  retrievalExampleDocuments,
} from "../../src/data/document-preview";

describe("corpus documentaire de démonstration", () => {
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
