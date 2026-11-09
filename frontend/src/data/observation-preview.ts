import { analysisVideos, type AnalysisVideo } from "./analysis-preview";

import type { Observation, ObservationQuality } from "./contracts";
export type { ObservationQuality } from "./contracts";
export type DemoObservation = Observation;
export const observationSpecies = [
  { value: "chevreuil", label: "Chevreuil" },
  { value: "renard", label: "Renard" },
  { value: "sanglier", label: "Sanglier" },
  { value: "blaireau", label: "Blaireau" },
  { value: "cerf-elaphe", label: "Cerf élaphe" },
  { value: "ecureuil", label: "Écureuil" },
];
export const observationSpeciesFilters = [
  { value: "", label: "Toutes les espèces" },
  ...observationSpecies,
];
export const observationAssignmentOptions = [
  { value: "", label: "Choisir une espèce" },
  ...observationSpecies,
];
export const observationQualityFilters = [
  { value: "", label: "Toutes les qualités" },
  { value: "clear", label: "Nettes" },
  { value: "blurry", label: "Floues" },
  { value: "too_small", label: "Trop petites" },
  { value: "near_duplicate", label: "Quasi identiques" },
];
export function observationSpeciesLabel(value: string) {
  return (
    observationSpecies.find((option) => option.value === value)?.label || value
  ).toLocaleLowerCase("fr-FR");
}
const deer = analysisVideos[0],
  squirrel = analysisVideos[2];
const qualities: ObservationQuality[] = [
  "blurry",
  "blurry",
  "too_small",
  "clear",
  "near_duplicate",
  "blurry",
  "clear",
  "clear",
];
const zooms = [
  "195% auto",
  "235% auto",
  "180% auto",
  "220% auto",
  "245% auto",
  "205% auto",
  "170% auto",
];
// Huit observations fictives. Les positions CSS sont des aperçus, jamais des recadrages extraits.
export const demoObservations: DemoObservation[] = Array.from(
  { length: 8 },
  (_, index) => {
    const realVideo = index === 7;
    const filename = realVideo
      ? squirrel.filename
      : `Chevreuil-Score-${271 + Math.floor(index / 2)}.mp4`;
    return {
      id: `observation-${index + 1}`,
      number: index + 1,
      filename,
      suggestedSpecies: realVideo ? "ecureuil" : "chevreuil",
      quality: qualities[index],
      protected: index === 5 || index === 6,
      status: "review",
      context: "15 s avant / 20 s après",
      media: realVideo
        ? { ...squirrel, detections: [] }
        : {
            ...deer,
            id: `observation-media-${index + 1}`,
            filename,
            duration: index === 1 ? 15 : 27,
            posterSize: zooms[index],
            posterPosition: `${index % 2 ? 96 : 90}% ${index % 3 ? 59 : 55}%`,
            detections: [],
          },
    };
  },
);
export function filterDemoObservations(
  observations: DemoObservation[],
  species: string,
  quality: string,
) {
  return observations.filter(
    (observation) =>
      (!species ||
        (observation.assignedSpecies || observation.suggestedSpecies) ===
          species) &&
      (!quality || observation.quality === quality),
  );
}
/** Ne retient que les observations visibles et éditables de cette page. */
export function editableSelection(
  visible: DemoObservation[],
  selected: ReadonlySet<string>,
) {
  return visible.filter(
    (observation) => !observation.protected && selected.has(observation.id),
  );
}
export function validateDemoObservations(
  observations: DemoObservation[],
  selected: ReadonlySet<string>,
  species: string,
) {
  if (!observationSpecies.some((option) => option.value === species))
    return observations;
  return observations.map((observation) =>
    selected.has(observation.id) && !observation.protected
      ? {
          ...observation,
          assignedSpecies: species,
          status: "validated" as const,
        }
      : observation,
  );
}
export function removeDemoObservations(
  observations: DemoObservation[],
  selected: ReadonlySet<string>,
) {
  return observations.filter(
    (observation) => observation.protected || !selected.has(observation.id),
  );
}
