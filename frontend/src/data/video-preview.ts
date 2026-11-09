import type { Video, VideoStatus } from "./contracts";
export type { VideoStatus } from "./contracts";
export type DemoVideo = Video;

export const videoStatusOptions = [
  { value: "", label: "Tous les statuts" },
  { value: "validated", label: "Validée" },
  { value: "pending", label: "En validation" },
  { value: "unanalysed", label: "À analyser" },
  { value: "ready", label: "Prête" },
  { value: "processing", label: "En cours" },
  { value: "no_detections", label: "Aucune détection" },
  { value: "error", label: "En erreur" },
  { value: "unknown", label: "Non renseigné" },
];
export const videoSpeciesOptions = [
  { value: "", label: "Toutes les espèces" },
  ...["Chevreuil", "Renard", "Blaireau", "Sanglier"].map((value) => ({
    value,
    label: value,
  })),
];
// Jeu de démonstration local : les 248 entrées sont fictives, sans vidéo réelle.
const examples: Omit<DemoVideo, "id" | "filename">[] = [
  {
    species: "Chevreuil",
    parcel: "Parcelle Nord",
    date: "12 mars 2025 - 22:14",
    duration: "00:27",
    status: "validated",
    thumbnail: "deer",
  },
  {
    species: "Renard",
    parcel: "Haie Ouest",
    date: "6 mars 2025 - 07:32",
    duration: "00:18",
    status: "pending",
    thumbnail: "fox",
  },
  {
    species: "Blaireau",
    parcel: "Prairie Sud",
    date: "28 fév. 2025 - 19:08",
    duration: "00:42",
    status: "validated",
    thumbnail: "badger",
  },
  {
    species: "Sanglier",
    parcel: "Parcelle Nord",
    date: "28 fév. 2025 - 20:17",
    duration: "00:35",
    status: "unanalysed",
    thumbnail: "boar",
  },
];
export const demoVideos: DemoVideo[] = Array.from(
  { length: 248 },
  (_, index) => ({
    ...examples[index % examples.length],
    id: `demo-video-${index + 124}`,
    filename: `VID_${String(index + 124).padStart(5, "0")}.mp4`,
  }),
);
export function filterDemoVideos(
  videos: DemoVideo[],
  query: string,
  species: string,
  status: string,
) {
  const normalize = (value: string) =>
    value
      .normalize("NFD")
      .replace(/\p{Diacritic}/gu, "")
      .toLocaleLowerCase("fr");
  const search = normalize(query.trim());
  return videos.filter(
    (video) =>
      (!species || video.species === species) &&
      (!status || video.status === status) &&
      (!search ||
        normalize(
          `${video.filename} ${video.parcel} ${video.species}`,
        ).includes(search)),
  );
}
