import { GLTFLoader, type GLTF } from "three/addons/loaders/GLTFLoader.js";
import { disposeScene } from "./world-utils";
import { Scene } from "three";
import inventory from "./content/spatial-assets.json";
export type SpatialId = keyof typeof inventory.assets;
export const spatialInventory = inventory;
const encodedCaches = new WeakMap<
  AbortSignal,
  Map<SpatialId, Promise<ArrayBuffer>>
>();
/** Keep one bounded compressed copy per world; release decoded/GPU objects independently. */
export async function spatialBytes(id: SpatialId, signal: AbortSignal) {
  if (signal.aborted) throw new DOMException("Aborted", "AbortError");
  let cache = encodedCaches.get(signal);
  if (!cache) {
    cache = new Map();
    encodedCaches.set(signal, cache);
    signal.addEventListener(
      "abort",
      () => {
        cache!.clear();
        encodedCaches.delete(signal);
      },
      { once: true },
    );
  }
  if (!cache.has(id)) {
    const pending = fetch(inventory.assets[id].url, { signal })
      .then((response) => {
        if (!response.ok) throw new Error(`Modèle local indisponible : ${id}`);
        return response.arrayBuffer();
      })
      .catch((error) => {
        cache!.delete(id);
        throw error;
      });
    cache.set(id, pending);
  }
  return cache.get(id)!;
}
export function disposeModel(model: GLTF) {
  const textures = new Set<ImageBitmap>();
  model.scene.traverse((object: any) => {
    for (const material of object.material ? [object.material].flat() : [])
      for (const value of Object.values(material) as any[])
        if (value?.isTexture && value.image?.close) textures.add(value.image);
  });
  const scene = new Scene();
  scene.add(model.scene);
  disposeScene(scene);
  textures.forEach((image) => image.close());
}
export async function loadSpatial(
  id: SpatialId,
  signal: AbortSignal,
): Promise<GLTF> {
  const model = await new GLTFLoader().parseAsync(
    await spatialBytes(id, signal),
    "",
  );
  if (signal.aborted) {
    disposeModel(model);
    throw new DOMException("Aborted", "AbortError");
  }
  return model;
}
