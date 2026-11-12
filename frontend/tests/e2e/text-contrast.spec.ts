import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const themes = [
  "forest",
  "sky",
  "river",
  "underwater",
  "wetland",
  "meadow",
  "coast",
  "night-forest",
];
for (const theme of themes) {
  test(`contraste des textes — ${theme}`, async ({ page }, info) => {
    test.setTimeout(120000);
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.addInitScript(
      (theme) => localStorage.setItem("symbiose:wallpaper:v1", theme),
      theme,
    );
    let connected = true;
    await page.route("**/api/**", (route) => {
      const path = new URL(route.request().url()).pathname.replace(
        /^\/api/,
        "",
      );
      const json = (json: unknown) => route.fulfill({ json });
      if (path === "/auth/me")
        return connected
          ? json({
              user: {
                id: "contrast-user",
                role: "admin",
                display_name: "Camille",
                email: "camille@example.test",
                created_at: "2026-11-12",
                deleted_at: null,
              },
              csrf_token: "test",
            })
          : route.fulfill({
              status: 401,
              json: { detail: "Connexion requise" },
            });
      if (path === "/auth/status") return json({ setup_required: false });
      if (path === "/console/dashboard")
        return json({
          counts: { videos: 1, species: 0, pending: 1, tasks: 0 },
          distribution: [],
          latest_training: null,
        });
      if (path === "/console/videos" || path === "/console/videos/video") {
        const video = {
          id: "video",
          filename: "Observation de terrain.mp4",
          species_candidate: "chevreuil",
          status: "ready",
          metadata: { duration_seconds: 12 },
          created_at: "2026-11-12",
        };
        return json(path === "/console/videos" ? [video] : video);
      }
      if (path === "/console/models")
        return json([
          {
            id: "model",
            name: "Modèle de terrain",
            status: "candidate",
            active: false,
            checkpoint_key: "models/checkpoint.pt",
            sha256: "a".repeat(64),
            metrics: {},
            metadata: {},
            created_at: "2026-11-12",
          },
        ]);
      if (path === "/documents/species" || path === "/review/species")
        return json([
          { name: "chevreuil", display_name: "Chevreuil", class_index: 0 },
        ]);
      if (path === "/documents")
        return json([
          {
            id: "document",
            title: "Étude des continuités écologiques et des habitats",
            published_date: "2026-01-01",
            status: "indexed",
            species_links: [{ species: "chevreuil" }],
            assets: [],
            language: "fr",
            metadata: {},
          },
        ]);
      if (path === "/parcels/options")
        return json({
          land_types: { pasture: "Pâturage" },
          project_types: { housing: "Habitation" },
        });
      if (path === "/parcels/videos/video")
        return json({ profile: null, dossier: null });
      return json([]);
    });
    const failures: unknown[] = [];
    async function scan(path: string) {
      await page.goto(path);
      await expect(page.locator("h1")).toBeVisible();
      await expect(page.locator("html")).toHaveAttribute(
        "data-environment",
        theme,
      );
      const result = await new AxeBuilder({ page })
        .withRules(["color-contrast"])
        .analyze();
      for (const violation of result.violations)
        for (const node of violation.nodes) {
          failures.push({
            path,
            target: node.target,
            summary: node.failureSummary,
          });
        }
      if (
        path === "/analyses?video=video" &&
        ["forest", "meadow"].includes(theme)
      ) {
        await page.screenshot({
          path: `test-results/contrast-${theme}.png`,
          fullPage: true,
        });
      }
    }
    for (const path of [
      "/",
      "/videos",
      "/parcelles",
      "/analyses?video=video",
      "/review",
      "/documents",
      "/profil",
      "/admin",
      "/admin/videos",
      "/admin/analyses?video=video",
      "/admin/datasets",
      "/admin/training",
      "/admin/models",
      "/admin/evaluation",
      "/admin/utilisateurs",
      "/admin/documents",
    ])
      await scan(path);
    connected = false;
    for (const path of ["/", "/connexion", "/inscription", "/reinitialiser"])
      await scan(path);
    await info.attach("text-contrast", {
      body: JSON.stringify(failures, null, 2),
      contentType: "application/json",
    });
    expect(failures).toEqual([]);
  });
}
