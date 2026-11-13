import inventory from "./content/runtime-assets.json";
import type { ChapterId } from "./config";

export function sceneAsset(
  id: ChapterId | string,
  role: "primary" | "foreground",
) {
  const scene = inventory.scenes[id as ChapterId];
  return scene ? scene[role].url : "";
}
export const posterUrl = inventory.poster.url;
export const runtimeInventory = inventory;
/** The shared canopy and logo stay pinned; other textures follow the camera window. */
export function textureWindow(index: number): string[] {
  const ids = Object.keys(inventory.scenes);
  return [
    ...new Set([
      "sky",
      "logo",
      ...ids.slice(Math.max(0, index - 1), Math.min(ids.length, index + 2)),
    ]),
  ];
}
