import { clamp01 } from "./journey";
export const checkpointKey = "symbiose-jury-checkpoint-v1";
export interface JuryCheckpoint {
  version: 1;
  progress: number;
  mode: "presentation" | "exploration";
}
export function readCheckpoint(
  storage?: Pick<Storage, "getItem">,
): JuryCheckpoint | undefined {
  try {
    const value = JSON.parse(
      (storage ?? localStorage).getItem(checkpointKey) || "null",
    );
    if (
      value?.version === 1 &&
      typeof value.progress === "number" &&
      Number.isFinite(value.progress) &&
      value.progress > 0 &&
      value.progress <= 1 &&
      ["presentation", "exploration"].includes(value.mode)
    )
      return value;
  } catch {
    /* Private browsing or damaged state must not prevent startup. */
  }
}
export function saveCheckpoint(
  progress: number,
  mode: JuryCheckpoint["mode"],
  storage?: Pick<Storage, "setItem">,
) {
  try {
    (storage ?? localStorage).setItem(
      checkpointKey,
      JSON.stringify({ version: 1, progress: clamp01(progress), mode }),
    );
  } catch {
    /* Best effort, no personal or application data are stored. */
  }
}
export function ownsPresentationKey(event: KeyboardEvent): boolean {
  if (
    ![
      "ArrowLeft",
      "ArrowRight",
      "ArrowUp",
      "ArrowDown",
      "PageUp",
      "PageDown",
      "Home",
      "End",
      " ",
    ].includes(event.key)
  )
    return false;
  const target = event.target instanceof Element ? event.target : null;
  if (
    target?.closest(
      "input,select,textarea,video,summary,dialog,[contenteditable]",
    )
  )
    return false;
  return !(event.key === " " && target?.closest("button,a"));
}
