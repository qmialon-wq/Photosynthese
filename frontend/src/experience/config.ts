export type Vec3 = readonly [number, number, number];
import { pitchChapters } from "./pitch";
import { sceneAsset } from "./runtime-assets";

export type ChapterId =
  | "forest"
  | "sky"
  | "rivers"
  | "underwater"
  | "wetland"
  | "meadow"
  | "coast"
  | "night-forest";
export interface CameraKey {
  time: number;
  position: Vec3;
  target: Vec3;
  fov: number;
}
export interface NarrativeChapter {
  id: ChapterId;
  name: string;
  status: "spatial-study";
  start: number;
  duration: number;
  assets: readonly {
    id: string;
    kind: "alpha";
    provisional: true;
    description: string;
    url: string;
  }[];
  camera: readonly CameraKey[];
  effects: {
    fog: string;
    density: number;
    light: string;
    exposure: number;
    particles: number;
  };
  texts: readonly {
    from: number;
    to: number;
    eyebrow: string;
    title: string;
    body: string;
  }[];
  transition: { in: string; out: string };
}
export const narrativeDuration = 210;
export const scrollScreens = 21;
export const cameraKeys: readonly CameraKey[] = [
  { time: 0, position: [0, 0.7, 18], target: [-2, 7, -28], fov: 57 },
  { time: 12, position: [1, 10, 0], target: [0, 34, -38], fov: 59 },
  { time: 23, position: [4, 34, -34], target: [9, 22, -120], fov: 59 },
  { time: 35, position: [4, 65, -85], target: [8, 45, -210], fov: 57 },
  { time: 48, position: [8, 28, -148], target: [6, 0, -234], fov: 57 },
  { time: 60, position: [6, 2.2, -210], target: [2, 0.5, -255], fov: 57 },
  { time: 72, position: [2, 0.45, -247], target: [-4, -1, -285], fov: 58 },
  { time: 83, position: [-4, -2.7, -280], target: [-6, -4, -323], fov: 59 },
  { time: 95, position: [-4, -5, -315], target: [0, -3, -365], fov: 59 },
  { time: 104, position: [-1, -3, -373], target: [4, 1, -412], fov: 58 },
  { time: 109, position: [3, -0.45, -400], target: [8, 2, -443], fov: 57 },
  { time: 115, position: [6, 1.7, -430], target: [14, 1.6, -458], fov: 57 },
  { time: 122, position: [7, 2.4, -444], target: [14, 1.6, -458], fov: 57 },
  { time: 133, position: [-4, 17, -488], target: [0, 2, -553], fov: 57 },
  { time: 150, position: [-20, 55, -550], target: [3, 1, -622], fov: 57 },
  { time: 165, position: [-8, 94, -622], target: [2, 6, -730], fov: 57 },
  { time: 180, position: [38, 48, -680], target: [-26, 19, -753], fov: 57 },
  { time: 190, position: [52, 62, -749], target: [-1, 18, -820], fov: 57 },
  { time: 201, position: [12, 20, -818], target: [0, 8, -866], fov: 57 },
  { time: 210, position: [0, 2.5, -865], target: [0, 5, -912], fov: 57 },
];
export const chapterIds: readonly ChapterId[] = [
  "forest",
  "sky",
  "rivers",
  "underwater",
  "wetland",
  "meadow",
  "coast",
  "night-forest",
];
const names = [
  "Forêt",
  "Ciel et nuages",
  "Rivières",
  "Monde sous-marin",
  "Zone humide",
  "Prairie et bocage",
  "Littoral — Étretat",
  "Forêt nocturne",
];
export const anchorTimes = [0, 35, 60, 95, 115, 150, 180, 210] as const;
const boundaries = [0, 17.5, 47.5, 77.5, 105, 132.5, 165, 195, 210];
export const chapters: readonly NarrativeChapter[] = chapterIds.map(
  (id, index) => ({
    id,
    name: names[index],
    status: "spatial-study",
    start: boundaries[index],
    duration: boundaries[index + 1] - boundaries[index],
    assets: [
      {
        id: `${id}-foreground`,
        kind: "alpha",
        provisional: true,
        description: "Premier plan généré, non documentaire",
        url: sceneAsset(id, "foreground"),
      },
    ],
    camera: cameraKeys.filter(
      (key) =>
        key.time >= boundaries[index] && key.time <= boundaries[index + 1],
    ),
    effects: {
      fog: index === 3 ? "#174641" : index === 7 ? "#142f36" : "#90a28c",
      density: index === 3 ? 0.038 : 0.007,
      light: index === 7 ? "#a4c5d1" : "#ffe4b2",
      exposure: 1.1,
      particles: index === 3 ? 120 : 80,
    },
    texts: [
      {
        from: 0,
        to: 1,
        eyebrow: `0${index + 1} / ${names[index].toLocaleUpperCase("fr")}`,
        title: pitchChapters[index].title,
        body: pitchChapters[index].message,
      },
    ],
    transition: {
      in: index ? `${chapterIds[index - 1]}-${id}` : "ground",
      out: index < 7 ? `${id}-${chapterIds[index + 1]}` : "logo",
    },
  }),
);
export const activeChapters = chapters;
