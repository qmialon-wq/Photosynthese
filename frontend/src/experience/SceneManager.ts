import { activeChapters, narrativeDuration } from "./config";
import { clamp01, smoothstep } from "./CameraController";

export function sceneAt(progress: number) {
  const time = clamp01(progress) * narrativeDuration;
  const chapter =
    activeChapters.find((item) => time < item.start + item.duration) ??
    activeChapters[activeChapters.length - 1];
  const local = clamp01((time - chapter.start) / chapter.duration);
  const text = chapter.texts.find(
    (item) => local >= item.from && local <= item.to,
  );
  let opacity = 0;
  if (text) {
    const enter =
      text.from === 0 ? 1 : smoothstep(text.from, text.from + 0.07, local);
    const exit =
      text.to === 1 ? 1 : 1 - smoothstep(text.to - 0.07, text.to, local);
    opacity = Math.min(enter, exit);
  }
  return { chapter, local, text, opacity };
}
