import { demoVideos as seedVideos } from "./video-preview";
import { demoProjects as seedProjects } from "./project-preview";
import { analysisVideos as seedAnalyses } from "./analysis-preview";
import {
  demoObservations as seedObservations,
  observationSpecies,
} from "./observation-preview";
import { demoScientificDocuments } from "./document-preview";
import { indicators } from "./home-preview";
import {
  resource,
  type Snapshot,
  type DataProvider,
  type HomeSummary,
} from "./contracts";

/** Un seul scénario lié par identifiants ; les compteurs sont dérivés, jamais recopiés. */
export function createDemoSnapshot(): Snapshot {
  const videos = seedVideos.map((video, index) => {
    const project =
      seedProjects.find((p) => p.name === video.parcel && index < 4) ||
      seedProjects[(index - 4 + seedProjects.length) % seedProjects.length];
    const seconds =
      Number(video.duration.slice(0, 2)) * 60 + Number(video.duration.slice(3));
    return {
      ...video,
      projectId: project.id,
      parcel: project.name,
      durationSeconds: seconds,
    };
  });
  const squirrel = videos[videos.length - 1];
  Object.assign(squirrel, {
    filename: seedAnalyses[2].filename,
    species: "Écureuil",
    duration: "00:06",
    durationSeconds: seedAnalyses[2].duration,
    thumbnail: undefined,
  });
  const analysisLinks = [videos[0], videos[1], squirrel];
  const analyses = seedAnalyses.map((media, index) => ({
    ...media,
    duration: analysisLinks[index].durationSeconds,
    id: `demo-analysis-${index + 1}`,
    videoId: analysisLinks[index].id,
    filename: analysisLinks[index].filename,
    provenance: "demo" as const,
    state: "completed",
    createdAt: "2025-03-12T10:00:00Z",
  }));
  const observations = seedObservations.map((observation, index) => {
    const media =
      analyses[index === 7 ? 2 : index === 3 || index === 4 ? 1 : 0];
    return {
      ...observation,
      videoId: media.videoId,
      filename: media.filename,
      suggestedSpecies:
        media.species === "écureuil" ? "ecureuil" : media.species,
      status:
        index === 0 || index === 3
          ? ("validated" as const)
          : ("review" as const),
      assignedSpecies: index === 0 || index === 3 ? media.species : undefined,
      media: {
        ...media,
        detections: [],
        ...(index < 3
          ? {
              posterSize: observation.media.posterSize,
              posterPosition: observation.media.posterPosition,
            }
          : {}),
      },
    };
  });
  const projects = seedProjects.map((project) => {
    const members = videos.filter((v) => v.projectId === project.id);
    return {
      ...project,
      videos: members.length,
      species: new Set(members.map((v) => v.species)).size,
      videoIds: members.map((v) => v.id),
    };
  });
  for (const video of videos) {
    const linked = observations.filter(
      (observation) => observation.videoId === video.id,
    );
    if (linked.length)
      video.status = linked.some(
        (observation) => observation.status === "review",
      )
        ? "pending"
        : "validated";
  }
  return {
    videos: resource(videos),
    projects: resource(projects),
    observations: resource(observations),
    analyses: resource(analyses),
    documents: resource(
      demoScientificDocuments.map((d) => ({
        ...d,
        dateNote: "(date fictive)",
      })),
    ),
    species: resource(observationSpecies.map((s) => ({ ...s }))),
  };
}
export class DemoDataProvider implements DataProvider {
  readonly id = "demo:normandie-v1";
  async load(
    signal: AbortSignal,
    publish: Parameters<DataProvider["load"]>[1],
  ) {
    const snapshot = createDemoSnapshot();
    if (signal.aborted) return;
    for (const key of Object.keys(snapshot) as (keyof Snapshot)[])
      publish(key, snapshot[key]);
  }
}
const count = (value: number | null) =>
  value == null ? "—" : value.toLocaleString("fr-FR");
export function summarize(snapshot: Snapshot, simulated: boolean): HomeSummary {
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
  const recommendations = simulated
    ? [
        {
          id: "demo-haies",
          title: "Maintenir et renforcer les haies",
          description:
            "Favorise le déplacement de la faune et améliore la connectivité des habitats.",
        },
        {
          id: "demo-prairies",
          title: "Préserver les prairies",
          description: "Conserver une mosaïque d’habitats.",
        },
        {
          id: "demo-eau",
          title: "Protéger les zones humides",
          description: "Préserver les points d’eau et leurs abords.",
        },
        {
          id: "demo-bois",
          title: "Maintenir les lisières",
          description: "Favoriser les continuités boisées.",
        },
      ]
    : snapshot.projects.data.flatMap(
        (project) => project.recommendations ?? [],
      );
  return {
    overview: [
      {
        icon: "pin",
        value: count(known("projects") ? snapshot.projects.data.length : null),
        label: simulated ? "Territoires" : "Dossiers",
        detail: simulated ? "en suivi" : "enregistrés",
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
        detail: simulated ? "à consulter" : "dans les dossiers consultés",
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
    score: simulated ? 78 : null,
    indicators: simulated ? indicators : [],
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
