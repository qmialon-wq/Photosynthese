import { afterEach, describe, expect, it, vi } from "vitest";
import { AssetPreloader } from "../../src/experience/AssetPreloader";
import { PerformanceMonitor } from "../../src/experience/PerformanceMonitor";
import { terrainY, riverX } from "../../src/experience/world-utils";
import { disposeScene } from "../../src/experience/world-utils";
import { createVegetation } from "../../src/experience/world-vegetation";
import { sampleCamera } from "../../src/experience/CameraController";
import { Scene, InstancedMesh, Matrix4, Vector3 } from "three";
import { textureWindow } from "../../src/experience/runtime-assets";
import { RefractionPass } from "../../src/experience/RefractionPass";
import { PerspectiveCamera } from "three";
import { CameraController } from "../../src/experience/CameraController";
import { createWorld } from "../../src/experience/world";
import { defaultLayers } from "../../src/experience/journey";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("journey resource lifecycle", () => {
  it("deduplicates window loads and releases decoded textures outside the camera neighborhood", async () => {
    const close = vi.fn(),
      fetcher = vi.fn(async () => ({ ok: true, blob: async () => new Blob() }));
    vi.stubGlobal("fetch", fetcher);
    vi.stubGlobal(
      "createImageBitmap",
      vi.fn(async () => ({ width: 1280, height: 720, close })),
    );
    const preloader = new AssetPreloader(),
      signal = new AbortController().signal;
    await Promise.all([
      preloader.load(signal, textureWindow(0)),
      preloader.load(signal, textureWindow(0)),
    ]);
    expect(fetcher).toHaveBeenCalledTimes(3);
    expect(preloader.residentCount).toBe(3);
    await preloader.load(signal, textureWindow(5));
    preloader.releaseExcept(textureWindow(5));
    expect(preloader.residentCount).toBe(5);
    expect(close).toHaveBeenCalledTimes(1);
    await preloader.load(signal, textureWindow(0));
    preloader.releaseExcept(textureWindow(0));
    expect(preloader.residentCount).toBe(3);
    expect(preloader.estimatedImageBytes).toBe((3 * 1280 * 720 * 4 * 4) / 3);
    preloader.dispose();
    expect(close).toHaveBeenCalledTimes(7);
  });
  it("uses one world pass on land and two passes only during immersion", () => {
    const renderer = { setRenderTarget: vi.fn(), render: vi.fn() },
      pass = new RefractionPass(),
      scene = new Scene(),
      camera = new PerspectiveCamera();
    pass.render(renderer as any, scene, camera, 0, 0);
    expect(renderer.render).toHaveBeenCalledTimes(1);
    pass.render(renderer as any, scene, camera, 1, 95);
    expect(renderer.render).toHaveBeenCalledTimes(3);
    pass.render(renderer as any, scene, camera, 0, 115);
    expect(renderer.render).toHaveBeenCalledTimes(4);
    pass.dispose();
  });
  it("reports a missing local layer and disposes the eight decoded bitmaps", async () => {
    const close = vi.fn();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => ({
        ok: !url.includes("/forest/"),
        status: 404,
        blob: async () => new Blob(),
      })),
    );
    vi.stubGlobal(
      "createImageBitmap",
      vi.fn(async () => ({ width: 16, height: 16, close })),
    );
    const preloader = new AssetPreloader(),
      result = await preloader.load(new AbortController().signal);
    expect(result.issues).toEqual([
      "/experience-art/forest/foreground-runtime.webp",
    ]);
    expect(result.textures.size).toBe(8);
    expect(
      preloader.resources.every((r) => r.url.startsWith("/experience-art/")),
    ).toBe(true);
    preloader.dispose();
    expect(close).toHaveBeenCalledTimes(8);
    expect(result.textures.size).toBe(0);
  });
  it("closes late decoded resources after unmount instead of attaching them", async () => {
    const close = vi.fn(),
      resolvers: Array<(bitmap: unknown) => void> = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: true, blob: async () => new Blob() })),
    );
    vi.stubGlobal(
      "createImageBitmap",
      vi.fn(() => new Promise((resolve) => resolvers.push(resolve))),
    );
    const preloader = new AssetPreloader(),
      abort = new AbortController(),
      loading = preloader.load(abort.signal);
    await vi.waitFor(() => expect(resolvers).toHaveLength(9));
    abort.abort();
    preloader.dispose();
    resolvers.forEach((resolve) => resolve({ close }));
    const result = await loading;
    expect(result.textures.size).toBe(0);
    expect(result.issues).toEqual([]);
    expect(close).toHaveBeenCalledTimes(9);
  });
});

describe("continuous movement monitoring", () => {
  it("ties aquatic appearances and night-cloud extinction to scroll-derived effects", () => {
    const world = createWorld(true), camera = new CameraController();
    const particles = world.scene.getObjectByName("particles")!;
    const fish = particles.children[1] as InstancedMesh;
    camera.update(60/210);world.apply(60/210,camera.camera,defaultLayers);
    expect(fish.visible).toBe(false);
    camera.update(95/210);const submerged = world.apply(95/210,camera.camera,defaultLayers);
    expect(fish.visible).toBe(true);
    expect((fish.material as any).opacity).toBeCloseTo(submerged.effects.immersion*.9);
    const clouds = world.scene.getObjectByName("atmosphere")!.children[1] as InstancedMesh;
    for(const t of [190,200,205,210,200,190]) {
      camera.update(t/210);const state=world.apply(t/210,camera.camera,defaultLayers);
      expect((clouds.material as any).uniforms.night.value).toBe(state.effects.night);
      expect(clouds.visible).toBe(state.effects.night<1);
    }
    world.dispose();
  });
  it("keeps the entire camera path outside the actual instanced field hedges", () => {
    const vegetation = createVegetation(true),
      hedges = vegetation.hedges.getObjectByName(
        "field-hedges",
      ) as InstancedMesh;
    const matrix = new Matrix4(),
      center = new Vector3(),
      scale = new Vector3(),
      collisions: number[] = [];
    for (let sample = 0; sample <= 800; sample++) {
      const p = sample / 800,
        pose = sampleCamera(p).position;
      for (let i = 0; i < hedges.count; i++) {
        hedges.getMatrixAt(i, matrix);
        center.setFromMatrixPosition(matrix);
        scale.setFromMatrixScale(matrix);
        if (scale.x === 0) continue;
        const distance =
          ((pose[0] - center.x) / scale.x) ** 2 +
          ((pose[1] - center.y) / scale.y) ** 2 +
          ((pose[2] - center.z) / scale.z) ** 2;
        if (distance < 1.1) collisions.push(p);
      }
    }
    disposeScene(new Scene().add(vegetation.group));
    expect(collisions).toEqual([]);
  });
  it("does not interpret screenshots or idle redraws as low performance", () => {
    vi.spyOn(document, "hidden", "get").mockReturnValue(false);
    const report = vi.fn(),
      downgrade = vi.fn(),
      monitor = new PerformanceMonitor(report, downgrade);
    for (let i = 1; i < 20; i++) monitor.frame(i * 700, true);
    expect(report).not.toHaveBeenCalled();
    expect(downgrade).not.toHaveBeenCalled();
    for (let i = 0; i < 200; i++) monitor.frame(14000 + i * 16.667, true);
    expect(report).toHaveBeenCalled();
    expect(report.mock.calls.at(-1)![0].fps).toBe(60);
    expect(downgrade).not.toHaveBeenCalled();
  });
  it("lowers resolution once after two genuinely slow continuous windows", () => {
    vi.spyOn(document, "hidden", "get").mockReturnValue(false);
    const downgrade = vi.fn(),
      monitor = new PerformanceMonitor(() => {}, downgrade);
    for (let i = 1; i < 170; i++) monitor.frame(i * 40, true);
    expect(downgrade).toHaveBeenCalledTimes(1);
  });
  it("keeps the river bed below its surface and the observation island above it", () => {
    for (const z of [-230, -280, -315, -375, -400])
      expect(terrainY(riverX(z), z)).toBeLessThan(0);
    expect(terrainY(14, -458)).toBeCloseTo(0.6);
  });
});
