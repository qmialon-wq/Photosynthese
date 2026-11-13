// @vitest-environment node
import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";
import {
  assetRoot,
  resourcePath,
  verifyAssets,
} from "../../scripts/experience-assets.mjs";

describe("visual production delivery", () => {
  it("checks the actual files, PNG alpha, hashes and copied brand without requiring a GPU", () => {
    expect(verifyAssets()).toMatchObject({
      scenes: 8,
      produced: 16,
      missing: 41,
      transitionWorkAllowed: false,
    });
  });
  it("keeps absent work explicit and each produced resource linked to an exact generation prompt", () => {
    const manifest = JSON.parse(
      readFileSync(path.join(assetRoot, "manifest.json"), "utf8"),
    );
    expect(manifest.approval).toMatchObject({
      mainPlatesApproved: false,
      layeredScenesReady: false,
      transitionWorkAllowed: false,
    });
    expect(manifest.disclosure).toMatch(/générées par IA/);
    for (const scene of manifest.scenes) {
      const primary = scene.resources.find(
        (resource: any) => resource.role === "primary",
      );
      const foreground = scene.resources.find(
        (resource: any) => resource.role === "foreground",
      );
      expect(primary.status).toBe("present-review-required");
      expect(foreground.alpha.min).toBe(0);
      expect(foreground.alpha.max).toBe(255);
      expect(foreground.dimensions).toMatchObject({
        width: primary.dimensions.width,
        height: primary.dimensions.height,
      });
      for (const resource of scene.resources) {
        if (resource.status === "missing") {
          expect(resource.path).toBeNull();
          expect(resource.dimensions).toBeNull();
          expect(resource.licenseId).toBe("not-acquired");
        } else {
          expect(resource.licenseId).toBe("generated-openai");
          expect(
            readFileSync(resourcePath(resource.generation.promptPath), "utf8")
              .length,
          ).toBeGreaterThan(200);
        }
      }
    }
    expect(manifest.scenes[6].disclosure).toMatch(
      /Évocation générée d’Étretat/,
    );
    expect(manifest.scenes[5].time).toEqual({
      start: 150,
      end: 240,
      duration: 90,
    });
  });
  it("rejects paths outside the portable asset directory", () => {
    expect(() => resourcePath("../private.png")).toThrow(/outside asset root/);
    expect(() =>
      resourcePath(path.resolve(assetRoot, "forest/primary-v1.png")),
    ).toThrow(/relative/);
  });
});
