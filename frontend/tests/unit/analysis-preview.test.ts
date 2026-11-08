import { describe, expect, it } from "vitest";
import { containedMedia, playbackTime } from "../../src/data/analysis-preview";

describe("alignement du calque dans la surface réelle du média", () => {
  it("centre une vidéo portrait sans placer le cadre dans les bandes latérales", () => {
    expect(containedMedia(900, 600, 1080, 1920)).toEqual({
      x: 0.3125,
      y: 0,
      width: 0.375,
      height: 1,
    });
  });
  it("conserve les proportions du paysage en plein écran et au redimensionnement", () => {
    const fullscreen = containedMedia(1600, 900, 1536, 1024);
    expect(fullscreen.width).toBeCloseTo(0.84375);
    expect(fullscreen.x).toBeCloseTo(0.078125);
    expect(containedMedia(240, 160, 1536, 1024)).toEqual({
      x: 0,
      y: 0,
      width: 1,
      height: 1,
    });
    expect(containedMedia(600, 900, 1920, 1080).height).toBeCloseTo(0.375);
  });
  it("reste stable avant le chargement des métadonnées", () => {
    expect(containedMedia(0, 0, NaN, 1024)).toEqual({
      x: 0,
      y: 0,
      width: 1,
      height: 1,
    });
  });
  it("formate les temps réels et les positions invalides", () => {
    expect(playbackTime(6.826667)).toBe("0:06");
    expect(playbackTime(93.9)).toBe("1:33");
    expect(playbackTime(NaN)).toBe("0:00");
    expect(playbackTime(-3)).toBe("0:00");
  });
});
