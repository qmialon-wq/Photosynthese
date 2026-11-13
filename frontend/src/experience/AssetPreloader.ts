import {
  SRGBColorSpace,
  Texture,
  type Camera,
  type Scene,
  type WebGLRenderer,
} from "three";
import { activeChapters } from "./config";
export class AssetPreloader {
  readonly resources = [
    ...activeChapters.flatMap((chapter) =>
      chapter.assets.map((asset) => ({ id: chapter.id, url: asset.url })),
    ),
    { id: "logo", url: "/experience-art/shared/symbiose-logo.png" },
  ];
  private textures = new Map<string, Texture>();
  private pending = new Map<string, Promise<void>>();
  private issues = new Set<string>();
  private disposed = false;
  get residentCount() {
    return this.textures.size;
  }
  get estimatedImageBytes() {
    let total = 0;
    for (const texture of this.textures.values()) {
      const image = texture.image as ImageBitmap;
      total += (image.width * image.height * 4 * 4) / 3;
    }
    return Math.round(total);
  }
  async load(signal: AbortSignal, ids?: readonly string[]) {
    await Promise.all(
      this.resources
        .filter((resource) => !ids || ids.includes(resource.id))
        .map(async (resource) => {
          if (this.textures.has(resource.id)) return;
          if (this.pending.has(resource.id))
            return this.pending.get(resource.id);
          const task = (async () => {
            const controller = new AbortController(),
              cancel = () => controller.abort();
            signal.addEventListener("abort", cancel, { once: true });
            const timeout = setTimeout(cancel, 8000);
            try {
              if (signal.aborted) throw new Error("aborted");
              const response = await fetch(resource.url, {
                signal: controller.signal,
              });
              if (!response.ok) throw new Error(String(response.status));
              const bitmap = await createImageBitmap(await response.blob(), {
                imageOrientation: "flipY",
                premultiplyAlpha: "none",
              });
              if (signal.aborted || this.disposed) {
                bitmap.close();
                return;
              }
              const texture = new Texture(bitmap);
              texture.colorSpace = SRGBColorSpace;
              texture.needsUpdate = true;
              this.textures.set(resource.id, texture);
              this.issues.delete(resource.url);
            } catch {
              if (!signal.aborted && !this.disposed)
                this.issues.add(resource.url);
            } finally {
              clearTimeout(timeout);
              signal.removeEventListener("abort", cancel);
              this.pending.delete(resource.id);
            }
          })();
          this.pending.set(resource.id, task);
          return task;
        }),
    );
    return { textures: this.textures, issues: [...this.issues] };
  }
  releaseExcept(ids: readonly string[]) {
    for (const [id, texture] of this.textures) {
      if (ids.includes(id)) continue;
      texture.dispose();
      (texture.image as ImageBitmap)?.close?.();
      this.textures.delete(id);
    }
  }
  async prepare(
    renderer: WebGLRenderer,
    scene: Scene,
    camera: Camera,
    signal: AbortSignal,
  ) {
    if (signal.aborted) return false;
    await renderer.compileAsync(scene, camera);
    return !signal.aborted;
  }
  dispose() {
    this.disposed = true;
    for (const texture of this.textures.values()) {
      texture.dispose();
      (texture.image as ImageBitmap)?.close?.();
    }
    this.textures.clear();
  }
}
