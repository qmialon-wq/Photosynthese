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
/** 3D scenery uses PBR maps; landscape plates belong exclusively to the 2D fallback. */
export function textureWindow(_index: number): string[] { return ["logo"]; }
