import { describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { BoxGeometry, Mesh, MeshBasicMaterial, PerspectiveCamera } from "three";
import {
  spatialInventory,
  spatialBytes,
} from "../../src/experience/spatial-resources";
import { projectAnimalBox } from "../../src/experience/world-fauna";
import { layoutAnimalLabels } from "../../src/experience/animal-labels";
import { logoParticleTargets } from "../../src/experience/logo-particles";

describe("local spatial delivery", () => {
  it("downloads each encoded model once per world and clears ownership on abort", async () => {
    const fetcher = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue({
        ok: true,
        arrayBuffer: async () => new ArrayBuffer(16),
      } as Response);
    try {
      const first = new AbortController(),
        second = new AbortController();
      await Promise.all([
        spatialBytes("buse", first.signal),
        spatialBytes("buse", first.signal),
      ]);
      expect(fetcher).toHaveBeenCalledTimes(1);
      await spatialBytes("buse", second.signal);
      expect(fetcher).toHaveBeenCalledTimes(2);
      first.abort();
      await expect(spatialBytes("buse", first.signal)).rejects.toThrow(
        "Aborted",
      );
      expect(fetcher).toHaveBeenCalledTimes(2);
      second.abort();
    } finally {
      fetcher.mockRestore();
    }
  });
  it("ships every registered resource with its actual bytes and checksum", () => {
    const mirror = JSON.parse(
      readFileSync("public/experience-models/inventory.json", "utf8"),
    );
    expect(mirror).toEqual(spatialInventory);
    for (const asset of Object.values(spatialInventory.assets)) {
      const file = readFileSync("public" + asset.url);
      expect(file.length).toBe(asset.bytes);
      expect(createHash("sha256").update(file).digest("hex")).toBe(
        asset.sha256,
      );
      if (!asset.url.endsWith(".glb")) continue;
      const length = file.readUInt32LE(12),
        gltf = JSON.parse(file.subarray(20, 20 + length).toString());
      expect(gltf.buffers.every((b: any) => !b.uri)).toBe(true);
      expect(
        (gltf.images || []).every(
          (image: any) => !image.uri && image.bufferView !== undefined,
        ),
      ).toBe(true);
    }
  });
  it("projects the actual object volume and rejects objects behind the camera", () => {
    const camera = new PerspectiveCamera(60, 16 / 9, 0.1, 100);
    camera.updateMatrixWorld();
    const mesh = new Mesh(new BoxGeometry(1, 1, 1), new MeshBasicMaterial());
    mesh.position.set(0, 0, -5);
    const box = projectAnimalBox(mesh, camera)!;
    expect(box.x).toBeLessThan(0.5);
    expect(box.x + box.width).toBeGreaterThan(0.5);
    mesh.position.z = 5;
    expect(projectAnimalBox(mesh, camera)).toBeUndefined();
    mesh.geometry.dispose();
    (mesh.material as MeshBasicMaterial).dispose();
  });
  it("separates overlapping captions while retaining their true box positions", () => {
    const animals = Array.from({ length: 3 }, (_, i) => ({
      id: String(i),
      label: "Poisson",
      x: 0.7 + 0.01 * i,
      y: 0.5,
      width: 0.03,
      height: 0.03,
      opacity: 1,
    }));
    const result = layoutAnimalLabels(animals);
    expect(new Set(result.map((a) => a.labelY)).size).toBe(3);
    expect(result.map((a) => a.x)).toEqual(animals.map((a) => a.x));
  });
  it("samples transparent logo outlines deterministically with no duplicated points", () => {
    const pixels = new Uint8ClampedArray(12 * 6 * 4);
    for (let y = 0; y < 3; y++)
      for (let x = 2; x < 10; x++) pixels[(y * 12 + x) * 4 + 3] = 255;
    const target = logoParticleTargets(pixels, 12, 6, 15);
    expect(target).toEqual(logoParticleTargets(pixels, 12, 6, 15));
    expect(target.length).toBe(30);
    expect(
      new Set(
        Array.from(
          { length: 15 },
          (_, i) => `${target[i * 2]},${target[i * 2 + 1]}`,
        ),
      ).size,
    ).toBe(15);
    expect(target[1]).toBeGreaterThan(0); // Top of the source remains the top in camera space.
    expect(logoParticleTargets(new Uint8ClampedArray(4), 1, 1).length).toBe(0);
  });
});
