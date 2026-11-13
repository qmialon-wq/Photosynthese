import {
  anchorTimes,
  chapterIds,
  narrativeDuration,
  type ChapterId,
} from "./config";
import { pitchIndex } from "./pitch";

export const clamp01 = (value: number) =>
  Math.min(1, Math.max(0, Number.isFinite(value) ? value : 0));
export function smoothstep(from: number, to: number, value: number) {
  const t = clamp01((value - from) / (to - from));
  return t * t * (3 - 2 * t);
}
export const transitionIds = [
  "ascent",
  "territory-dive",
  "immersion",
  "emergence",
  "observation-data",
  "territory-coast",
  "living-cycle",
] as const;
export type TransitionId = (typeof transitionIds)[number];
const names = [
  "Forêt → Ciel",
  "Ciel → Rivière",
  "Rivière → Sous-marin",
  "Sous-marin → Marais",
  "Marais → Bocage",
  "Bocage → Littoral",
  "Littoral → Forêt nocturne",
];
export const transitions = transitionIds.map((id, index) => ({
  id,
  index,
  name: names[index],
  from: chapterIds[index],
  to: chapterIds[index + 1],
  start: anchorTimes[index],
  end: anchorTimes[index + 1],
}));
export function transitionProgress(id: TransitionId, local: number) {
  const t = transitions.find((item) => item.id === id)!;
  return (t.start + clamp01(local) * (t.end - t.start)) / narrativeDuration;
}
export function transitionAt(progress: number) {
  const time = clamp01(progress) * narrativeDuration;
  const spec = transitions.find((item) => time < item.end) ?? transitions[6];
  return {
    ...spec,
    local: clamp01((time - spec.start) / (spec.end - spec.start)),
    time,
  };
}
export interface JourneyLayers {
  terrain: boolean;
  vegetation: boolean;
  water: boolean;
  atmosphere: boolean;
  observation: boolean;
  particles: boolean;
  reference: boolean;
}
export const defaultLayers: JourneyLayers = {
  terrain: true,
  vegetation: true,
  water: true,
  atmosphere: true,
  observation: true,
  particles: true,
  reference: false,
};
export function sampleEffects(progress: number, altitude: number) {
  const time = clamp01(progress) * narrativeDuration;
  return {
    time,
    immersion:
      (1 - smoothstep(-0.65, 0.5, altitude)) *
      smoothstep(60, 78, time) *
      (1 - smoothstep(110, 116, time)),
    night: smoothstep(181, 202, time),
    map:
      smoothstep(36, 49, time) * (1 - smoothstep(54, 61, time)) +
      smoothstep(139, 150, time) * (1 - smoothstep(171, 179, time)),
    observation: smoothstep(117, 122, time) * (1 - smoothstep(140, 147, time)),
    dataMorph: smoothstep(124, 140, time),
    logo: smoothstep(198, 210, time),
    bubbleRise: smoothstep(95, 115, time),
  };
}
export function reducedProgress(progress: number) {
  return anchorTimes[pitchIndex(progress)] / narrativeDuration;
}
export function referenceScene(progress: number): ChapterId {
  const s = transitionAt(progress);
  return s.local < 0.5 ? s.from : s.to;
}
