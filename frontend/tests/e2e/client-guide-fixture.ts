import type { Page } from "@playwright/test";
import { resolve } from "node:path";

export async function guideFixture(
  page: Page,
  seen: string | null = "2026-11-12T10:00:00Z",
) {
  let seenAt = seen;
  let marks = 0;
  const videos = ["premiere", "seconde"].map((id) => ({
    id,
    filename: `${id}-capture.mp4`,
    species_candidate: null,
    status: "ready",
    created_at: "2026-11-12T08:00:00Z",
    metadata: {
      poster_url: "/src/assets/video-boar.png",
      duration_seconds: 18,
    },
  }));
  await page.route("**/api/**", (route) => {
    const path = new URL(route.request().url()).pathname.replace(/^\/api/, "");
    const reply = (json: unknown) => route.fulfill({ json });
    if (path === "/auth/me" || path === "/auth/login")
      return reply({
        user: {
          id: "guide-client",
          display_name: "Camille",
          role: "client",
          email: "camille@example.test",
          created_at: "2026-11-12",
          deleted_at: null,
          client_guide_seen_at: seenAt,
        },
        csrf_token: "guide-csrf",
      });
    if (path === "/auth/status") return reply({ setup_required: false });
    if (path === "/auth/client-guide/seen") {
      marks++;
      seenAt = "2026-11-12T10:00:00Z";
      return reply({ seen_at: seenAt });
    }
    if (path === "/console/videos") return reply(videos);
    if (path === "/console/videos/premiere") return reply(videos[0]);
    if (path === "/console/videos/premiere/file")
      return route.fulfill({
        path: resolve("src/assets/squirrel-local.mp4"),
        contentType: "video/mp4",
      });
    if (path === "/console/models")
      return reply([
        {
          id: "model",
          name: "Classificateur actif",
          active: true,
          status: "active",
          metadata: {},
          metrics: {},
        },
      ]);
    if (path === "/parcels/options")
      return reply({
        land_types: { pasture: "Pâturage" },
        project_types: { housing: "Habitation" },
      });
    if (path.startsWith("/parcels/videos/"))
      return reply({ profile: null, dossier: null });
    if (path === "/review/species" || path === "/documents/species")
      return reply([
        { name: "chevreuil", display_name: "Chevreuil", class_index: 0 },
      ]);
    if (path === "/review/samples")
      return reply(
        [0, 1].map((index) => ({
          id: `sample-${index}`,
          video_id: "premiere",
          original_name: "capture.mp4",
          frame_index: index + 1,
          revision: 0,
          state: "pending",
          label: null,
          species_candidate: null,
          predicted_label: null,
          test_locked: false,
          render_status: "ready",
          split: "train",
          quality: {},
          frame_quality: {},
          box: { x: 0.1, y: 0.1, w: 0.7, h: 0.7 },
          original_box: { x: 0.1, y: 0.1, w: 0.7, h: 0.7 },
        })),
      );
    if (path.includes("/images/"))
      return route.fulfill({
        path: resolve("src/assets/video-boar.png"),
        contentType: "image/png",
      });
    if (path === "/documents")
      return reply([
        {
          id: "example",
          title: "Exemple de publication : habitats et continuités écologiques",
          language: "fr",
          status: "indexed",
          species_links: [{ species: "chevreuil" }],
          assets: [],
          metadata: {},
        },
      ]);
    return reply([]);
  });
  return { marks: () => marks };
}
