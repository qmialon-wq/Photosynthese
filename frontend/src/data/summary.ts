import type { Snapshot, HomeSummary } from "./contracts";

const count = (value: number | null) =>
  value == null ? "—" : value.toLocaleString("fr-FR");
export function summarize(snapshot: Snapshot): HomeSummary {
  const known = <K extends keyof Snapshot>(key: K) =>
    ["success", "empty"].includes(snapshot[key].state) &&
    snapshot[key].complete;
  const videos = snapshot.videos.data,
    observations = snapshot.observations.data;
  const durationSeconds = videos.reduce(
    (sum, video) => sum + (video.durationSeconds || 0),
    0,
  );
  const species = new Set(
    observations
      .filter((o) => o.status === "validated")
      .map((o) => o.assignedSpecies)
      .filter(Boolean),
  );
  const recommendations = snapshot.projects.data.flatMap(
    (project) => project.recommendations ?? [],
  );
  return {
    overview: [
      {
        icon: "pin",
        value: count(known("projects") ? snapshot.projects.data.length : null),
        label: "Dossiers",
        detail: "enregistrés",
      },
      {
        icon: "camera",
        value: count(known("observations") ? observations.length : null),
        label: "Observations",
        detail: "disponibles",
      },
      {
        icon: "paw",
        value: count(known("observations") ? species.size : null),
        label: "Espèces identifiées",
        detail: "(validées)",
      },
      {
        icon: "leaf",
        value: count(known("projects") ? recommendations.length : null),
        label: "Recommandations",
        detail: "dans les dossiers consultés",
      },
    ],
    videoOverview: [
      {
        icon: "video",
        value: count(known("videos") ? videos.length : null),
        label: "Vidéos importées",
        detail: "",
      },
      {
        icon: "clock",
        value:
          known("videos") && videos.every((v) => v.durationSeconds != null)
            ? durationSeconds < 60
              ? `${durationSeconds.toLocaleString("fr-FR", { maximumFractionDigits: 1 })} s`
              : `${Math.floor(durationSeconds / 60)} min`
            : "—",
        label: "Durée totale",
        detail: "",
      },
      {
        icon: "layers",
        value: count(known("projects") ? snapshot.projects.data.length : null),
        label: "Dossiers",
        detail: "",
      },
    ],
    score: null,
    indicators: [],
    recommendations,
    latestAnalyses: snapshot.analyses.data.slice(0, 3).map((analysis) => {
      const video = videos.find((v) => v.id === analysis.videoId);
      const items = observations.filter((o) => o.videoId === analysis.videoId);
      return {
        id: analysis.id,
        name: video?.parcel || analysis.filename,
        date: analysis.createdAt
          ? new Date(analysis.createdAt).toLocaleDateString("fr-FR")
          : "—",
        status:
          analysis.state === "completed" ? "Terminée" : analysis.state || "—",
        validated: analysis.state === "completed",
        species: known("observations")
          ? new Set(items.map((o) => o.assignedSpecies).filter(Boolean)).size
          : null,
        observations: known("observations") ? items.length : null,
        thumbnail: video?.thumbnail,
        source: video?.source,
        poster: video?.poster,
      };
    }),
  };
}
