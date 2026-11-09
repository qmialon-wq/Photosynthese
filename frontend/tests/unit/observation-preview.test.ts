import { describe, expect, it } from "vitest";
import {
  demoObservations,
  editableSelection,
  filterDemoObservations,
  removeDemoObservations,
  validateDemoObservations,
} from "../../src/data/observation-preview";

describe("observations de validation en démonstration", () => {
  it("ne sélectionne que les observations visibles et éditables", () => {
    const visible = filterDemoObservations(
      demoObservations,
      "chevreuil",
      "blurry",
    );
    const attempted = new Set(demoObservations.map((o) => o.id));
    expect(editableSelection(visible, attempted).map((o) => o.id)).toEqual([
      "observation-1",
      "observation-2",
    ]);
    expect(
      editableSelection(
        visible,
        new Set(["unknown", "observation-8", "observation-6"]),
      ),
    ).toEqual([]);
  });
  it("valide localement sans altérer les suggestions ni les données initiales", () => {
    const before = JSON.stringify(demoObservations);
    const result = validateDemoObservations(
      demoObservations,
      new Set(["observation-1"]),
      "renard",
    );
    expect(result[0]).toMatchObject({
      assignedSpecies: "renard",
      suggestedSpecies: "chevreuil",
      status: "validated",
      filename: demoObservations[0].filename,
    });
    expect(result[1]).toBe(demoObservations[1]);
    expect(JSON.stringify(demoObservations)).toBe(before);
    expect(
      filterDemoObservations(result, "renard", "blurry").map((o) => o.id),
    ).toEqual(["observation-1"]);
  });
  it("protège les images de test même face à une sélection invalide", () => {
    const selected = new Set(demoObservations.map((o) => o.id));
    const protectedBefore = demoObservations.filter((o) => o.protected);
    expect(
      validateDemoObservations(demoObservations, selected, "renard").filter(
        (o) => o.protected,
      ),
    ).toEqual(protectedBefore);
    expect(removeDemoObservations(demoObservations, selected)).toEqual(
      protectedBefore,
    );
  });
  it("ignore une espèce inconnue sans attribuer de faux résultat", () => {
    expect(
      validateDemoObservations(
        demoObservations,
        new Set(["observation-1"]),
        "unknown",
      ),
    ).toBe(demoObservations);
  });
  it("retire les cartes demandées sans modifier la source", () => {
    const result = removeDemoObservations(
      demoObservations,
      new Set(["observation-1", "missing"]),
    );
    expect(result).toHaveLength(7);
    expect(demoObservations).toHaveLength(8);
    expect(result.some((o) => o.id === "observation-1")).toBe(false);
  });
});
