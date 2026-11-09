import { describe, expect, it } from "vitest";
import { demoVideos, filterDemoVideos } from "../../src/data/video-preview";
describe("données de démonstration de la Vidéothèque", () => {
  it("propose 248 identifiants distincts et les quatre vidéos de référence", () => {
    expect(demoVideos).toHaveLength(248);
    expect(new Set(demoVideos.map((video) => video.id)).size).toBe(248);
    expect(demoVideos.slice(0, 4).map((video) => video.filename)).toEqual([
      "VID_00124.mp4",
      "VID_00125.mp4",
      "VID_00126.mp4",
      "VID_00127.mp4",
    ]);
    expect(demoVideos.at(-1)?.filename).toBe("VID_00371.mp4");
  });
  it("recherche un nom de fichier, une parcelle ou une espèce sans distinction de casse ou d’accents", () => {
    expect(
      filterDemoVideos(demoVideos, "  vid_00124  ", "", "").map(
        (video) => video.id,
      ),
    ).toEqual(["demo-video-124"]);
    expect(filterDemoVideos(demoVideos, "PARCELLE nord", "", "")).toHaveLength(
      124,
    );
    expect(filterDemoVideos(demoVideos, "sangliér", "", "")).toHaveLength(62);
  });
  it("combine les filtres et retourne un résultat vide pour une combinaison absente", () => {
    expect(filterDemoVideos(demoVideos, "", "Renard", "pending")).toHaveLength(
      62,
    );
    expect(filterDemoVideos(demoVideos, "", "Renard", "validated")).toEqual([]);
    expect(filterDemoVideos(demoVideos, "inexistant", "", "")).toEqual([]);
  });
});
