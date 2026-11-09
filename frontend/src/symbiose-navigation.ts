export const symbioseNavigation = [
  { path: "/", label: "Accueil", icon: "grid" },
  { path: "/videos", label: "Vidéothèque", icon: "video" },
  { path: "/parcelles", label: "Mes dossiers", icon: "folder" },
  { path: "/analyses", label: "Analyses", icon: "sparkles" },
  { path: "/review", label: "Validation humaine", icon: "check-square" },
  { path: "/documents", label: "Documents scientifiques", icon: "document" },
] as const;
export const ACTIVE_WHEEL_SLOT = 3;
export const wheelSlots = [
  { x: 230, y: 187 },
  { x: 171, y: 263 },
  { x: 133, y: 349 },
  { x: 161, y: 449 },
  { x: 133, y: 545 },
  { x: 171, y: 628 },
] as const;
export function wheelSlot(index: number, activeIndex: number): number {
  return (index - activeIndex + ACTIVE_WHEEL_SLOT + 6) % 6;
}
