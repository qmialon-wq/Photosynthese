import deerPoster from "../assets/analysis-deer.png";
import photoSheet from "../assets/biodiversity-thumbnails.png";
import forestPoster from "../assets/auth-forest.png";
import squirrelVideo from "../assets/squirrel-local.mp4";

import type { AnalysisVideo } from "./contracts";
export type { AnalysisVideo, Detection } from "./contracts";
// Les résultats et le modèle ci-dessous sont fictifs, y compris sur la vidéo locale.
export const analysisVideos: AnalysisVideo[] = [
  {
    id: "deer-demo",
    filename: "Chevreuil-Scene-073.mp4",
    species: "chevreuil",
    kind: "poster",
    poster: deerPoster,
    duration: 33,
    width: 1536,
    height: 1024,
    detections: [
      {
        id: "deer-1",
        label: "Chevreuil",
        confidence: 0.94,
        bounds: { x: 0.645, y: 0.36, width: 0.285, height: 0.395 },
      },
    ],
  },
  {
    id: "fox-demo",
    filename: "Renard-Scene-018.mp4",
    species: "renard",
    kind: "poster",
    poster: photoSheet,
    posterSize: "200% 200%",
    posterPosition: "left bottom",
    duration: 18,
    width: 768,
    height: 512,
    detections: [
      {
        id: "fox-1",
        label: "Renard",
        confidence: 0.91,
        bounds: { x: 0.07, y: 0.12, width: 0.76, height: 0.76 },
      },
    ],
  },
  {
    id: "squirrel-local",
    filename: "19136320-hd_1080_1920_50fps.mp4",
    species: "écureuil",
    kind: "video",
    source: squirrelVideo,
    poster: forestPoster,
    duration: 6.826667,
    width: 1080,
    height: 1920,
    detections: [
      {
        id: "squirrel-1",
        label: "Écureuil",
        confidence: 0.92,
        bounds: { x: 0.24, y: 0.36, width: 0.54, height: 0.28 },
      },
    ],
  },
];
export const analysisObjectives = [
  { value: "species", label: "Identifier les espèces" },
  { value: "presence", label: "Repérer la présence d’animaux" },
  { value: "observations", label: "Visualiser les observations" },
];
export const analysisDetailOptions = [
  { value: "fast", label: "Rapide — une image sur 10" },
  { value: "balanced", label: "Équilibré — une image sur 5" },
  { value: "fine", label: "Détaillé — chaque image" },
];
export const modelCaption =
  "Modèle actif : convnext_tiny · 67e1b77d. Les espèces proposées restent à confirmer.";
export const detailCaptions: Record<string, string> = {
  fast: "Le mode rapide peut manquer un animal présent très brièvement. Les réglages techniques sont accessibles dans l’administration.",
  balanced:
    "Le mode équilibré illustre un échantillonnage plus régulier. Les réglages techniques sont accessibles dans l’administration.",
  fine: "Le mode détaillé illustre la lecture de chaque image. Les réglages techniques sont accessibles dans l’administration.",
};
export const simulationSteps = [10, 25, 42, 60, 78, 92, 100];
export const simulationStepDuration = 250;

export { containedMedia, playbackTime } from "./media";
