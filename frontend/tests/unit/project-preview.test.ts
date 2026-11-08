import { describe, expect, it } from "vitest";
import {
  demoProjects,
  filterDemoProjects,
} from "../../src/data/project-preview";
describe("dossiers de démonstration", () => {
  it("présente les six dossiers de référence et douze identifiants distincts", () => {
    expect(demoProjects).toHaveLength(12);
    expect(new Set(demoProjects.map((project) => project.id)).size).toBe(12);
    expect(
      demoProjects
        .slice(0, 6)
        .map(({ name, videos, species, status }) => [
          name,
          videos,
          species,
          status,
        ]),
    ).toEqual([
      ["Parcelle Nord", 42, 3, "validated"],
      ["Haie Ouest", 18, 2, "pending"],
      ["Prairie Sud", 67, 4, "unanalysed"],
      ["Zone Humide", 28, 5, "validated"],
      ["Forêt Est", 36, 6, "validated"],
      ["Bocage Central", 57, 3, "pending"],
    ]);
  });
  it("recherche uniquement dans le nom, sans distinction de casse ou d’accents", () => {
    expect(
      filterDemoProjects(demoProjects, "  FORET  ", "", "").map(
        (project) => project.name,
      ),
    ).toEqual(["Forêt Est"]);
    expect(filterDemoProjects(demoProjects, "prairie", "", "")).toHaveLength(2);
    expect(filterDemoProjects(demoProjects, "42", "", "")).toEqual([]);
  });
  it("combine les projets et statuts sans modifier les données", () => {
    expect(
      filterDemoProjects(demoProjects, "", "forest", "validated"),
    ).toHaveLength(4);
    expect(filterDemoProjects(demoProjects, "", "forest", "pending")).toEqual(
      [],
    );
    expect(
      filterDemoProjects(demoProjects, "", "wetland", "validated").map(
        (project) => project.name,
      ),
    ).toEqual(["Zone Humide"]);
    expect(demoProjects).toHaveLength(12);
  });
});
