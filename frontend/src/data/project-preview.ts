import type { Project } from "./contracts";
export type DemoProject = Project;
// Douze dossiers de présentation, sans identifiant ou donnée métier réelle.
export const demoProjects: DemoProject[] = [
  {
    id: "demo-nord",
    name: "Parcelle Nord",
    videos: 42,
    species: 3,
    status: "validated",
    project: "forest",
    landscape: "forest",
  },
  {
    id: "demo-haie",
    name: "Haie Ouest",
    videos: 18,
    species: 2,
    status: "pending",
    project: "hedgerow",
    landscape: "valley",
  },
  {
    id: "demo-prairie",
    name: "Prairie Sud",
    videos: 67,
    species: 4,
    status: "unanalysed",
    project: "meadow",
    landscape: "wetland",
  },
  {
    id: "demo-humide",
    name: "Zone Humide",
    videos: 28,
    species: 5,
    status: "validated",
    project: "wetland",
    landscape: "meadow",
  },
  {
    id: "demo-est",
    name: "Forêt Est",
    videos: 36,
    species: 6,
    status: "validated",
    project: "forest",
    landscape: "forest",
  },
  {
    id: "demo-bocage",
    name: "Bocage Central",
    videos: 57,
    species: 3,
    status: "pending",
    project: "bocage",
    landscape: "bocage",
  },
  {
    id: "demo-ruisseau",
    name: "Bois du Ruisseau",
    videos: 24,
    species: 4,
    status: "validated",
    project: "forest",
    landscape: "forest",
  },
  {
    id: "demo-verger",
    name: "Verger Nord",
    videos: 15,
    species: 3,
    status: "pending",
    project: "bocage",
    landscape: "bocage",
  },
  {
    id: "demo-lisiere",
    name: "Lisière Ouest",
    videos: 31,
    species: 5,
    status: "validated",
    project: "forest",
    landscape: "valley",
  },
  {
    id: "demo-fleurie",
    name: "Prairie Fleurie",
    videos: 22,
    species: 4,
    status: "unanalysed",
    project: "meadow",
    landscape: "meadow",
  },
  {
    id: "demo-mare",
    name: "Mare du Moulin",
    videos: 12,
    species: 6,
    status: "pending",
    project: "wetland",
    landscape: "wetland",
  },
  {
    id: "demo-saules",
    name: "Haie des Saules",
    videos: 19,
    species: 3,
    status: "validated",
    project: "hedgerow",
    landscape: "bocage",
  },
];
export const projectTypeOptions = [
  { value: "", label: "Tous les projets" },
  { value: "forest", label: "Suivi forestier" },
  { value: "hedgerow", label: "Préservation des haies" },
  { value: "meadow", label: "Gestion des prairies" },
  { value: "wetland", label: "Suivi des zones humides" },
  { value: "bocage", label: "Préservation du bocage" },
];
export const projectStatusOptions = [
  { value: "", label: "Tous les statuts" },
  { value: "validated", label: "Validé" },
  { value: "pending", label: "En validation" },
  { value: "unanalysed", label: "À analyser" },
];
export function filterDemoProjects(
  projects: DemoProject[],
  query: string,
  type: string,
  status: string,
) {
  const normalize = (value: string) =>
    value
      .normalize("NFD")
      .replace(/\p{Diacritic}/gu, "")
      .toLocaleLowerCase("fr");
  const search = normalize(query.trim());
  return projects.filter(
    (project) =>
      (!type || project.project === type) &&
      (!status || project.status === status) &&
      (!search || normalize(project.name).includes(search)),
  );
}
