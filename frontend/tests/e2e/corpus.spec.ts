import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const group = "22222222-2222-4222-8222-222222222222";
const analysis = [
  "11111111-1111-4111-8111-111111111111",
  "33333333-3333-4333-8333-333333333333",
];
const videos = ["A.mp4", "B.mp4"].map((filename, i) => ({
  id: `v${i}`,
  filename,
  status: "ready",
  metadata: {},
  created_at: "2026-10-23T10:00:00Z",
  species_candidate: null,
}));
const entries = videos.map((v, i) => ({
  video_id: v.id,
  filename: v.filename,
  analysis_id: analysis[i],
  analysis_status: i ? "queued" : "completed",
}));

test("sélection de plusieurs vidéos, formulaire unique et dossier commun persistant", async ({
  page,
}) => {
  let profile: Record<string, unknown> | null = null,
    started = false,
    complete = false;
  await page.context().route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    let data: unknown = [];
    if (path.endsWith("/console/videos")) data = videos;
    else if (path.endsWith("/parcels/options"))
      data = {
        land_types: { pasture: "Pâturage" },
        project_types: { housing: "Habitation" },
      };
    else if (
      path.endsWith("/parcels/corpora") &&
      route.request().method() === "POST"
    ) {
      expect(route.request().postDataJSON().video_ids).toEqual(["v0", "v1"]);
      data = { id: group };
    } else if (path.endsWith("/profile")) {
      profile = route.request().postDataJSON();
      data = { revision: 1 };
    } else if (path.endsWith("/dossiers")) {
      started = true;
      data = { id: "dossier" };
    } else if (path.endsWith(`/corpora/${group}`))
      data = {
        id: group,
        videos: entries,
        profile: profile ? { revision: 1, profile } : null,
        dossier: started
          ? {
              id: "dossier",
              status: complete ? "completed" : "waiting_analysis",
              video_count: 2,
              completed_video_count: complete ? 2 : 1,
              profile_revision: 1,
              videos: entries,
              result: complete
                ? {
                    video_count: 2,
                    status: "insufficient_sources",
                    observation_summary: "Deux vidéos analysées.",
                    confirmed_species: [],
                    predicted_species: [],
                    recommendations: [],
                    sources: [],
                    green_space: { message: "Pourcentage non déterminé." },
                    videos: entries.map((e) => ({
                      ...e,
                      annotated_video_url: `/console/tasks/${e.analysis_id}/artifacts/video`,
                    })),
                  }
                : null,
            }
          : null,
      };
    await route.fulfill({ json: data });
  });
  await page.goto("/videos");
  await page.getByLabel("Sélectionner A.mp4").check();
  await page.getByLabel("Sélectionner B.mp4").check();
  await page
    .getByRole("button", {
      name: "Préparer un dossier (2 vidéos)",
      exact: true,
    })
    .click();
  await expect(page).toHaveURL(new RegExp(`/parcelles/${group}`));
  await page.getByLabel("Surface de la parcelle (m²)").fill("2500");
  await page
    .getByRole("combobox", { name: "Type de parcelle", exact: true })
    .selectOption("pasture");
  await page
    .getByRole("combobox", { name: "Projet souhaité", exact: true })
    .selectOption("housing");
  await page
    .getByRole("button", {
      name: "Analyser les vidéos et préparer mon dossier",
    })
    .click();
  await expect(
    page.getByRole("status").filter({ hasText: "1 / 2 vidéos analysées" }),
  ).toBeVisible();
  complete = true;
  await expect(
    page.getByRole("link", { name: "Télécharger mon dossier commun (.txt)" }),
  ).toBeVisible({ timeout: 10000 });
  await expect(page.getByRole("link", { name: /MP4 annoté/ })).toHaveCount(2);
  const scan = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(
    scan.violations.map((v) => ({
      id: v.id,
      targets: v.nodes.map((n) => n.target),
    })),
  ).toEqual([]);
  await page.reload();
  await expect(page.getByLabel("Surface de la parcelle (m²)")).toHaveValue(
    "2500",
  );
  await expect(page.getByRole("link", { name: /MP4 annoté/ })).toHaveCount(2);
  await expect(
    page.getByRole("link", { name: "Télécharger mon dossier commun (.txt)" }),
  ).toHaveAttribute("href", "/api/parcels/dossiers/dossier/export");
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});

test("import de plusieurs fichiers et suivi groupé sans une boucle de polling par vidéo", async ({
  page,
}) => {
  let uploads = 0;
  const taskIds = [
    "11111111-1111-4111-8111-111111111111",
    "33333333-3333-4333-8333-333333333333",
  ];
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    let data: unknown = [];
    if (path.endsWith("/console/uploads"))
      data = { id: `upload-${uploads++}`, chunk_size: 4194304 };
    else if (path.includes("/chunks/")) data = { size: 4 };
    else if (path.endsWith("/complete"))
      data = { id: taskIds[path.includes("upload-0") ? 0 : 1] };
    else if (path.endsWith("/parcels/import-status"))
      data = route
        .request()
        .postDataJSON()
        .task_ids.map((id: string) => ({
          id,
          status: "completed",
          result: { video_id: `v${taskIds.indexOf(id)}` },
          error: null,
        }));
    else if (path.endsWith("/console/videos")) data = videos;
    await route.fulfill({ json: data });
  });
  await page.goto("/videos");
  await page
    .getByLabel("Importer une ou plusieurs vidéos", { exact: true })
    .setInputFiles(
      videos.map((v) => ({
        name: v.filename,
        mimeType: "video/mp4",
        buffer: Buffer.from("test"),
      })),
    );
  await expect(
    page.getByRole("button", {
      name: "Préparer un dossier (2 vidéos)",
      exact: true,
    }),
  ).toBeEnabled({ timeout: 10000 });
  await expect(page.getByLabel("Sélectionner A.mp4")).toBeChecked();
  await expect(page.getByLabel("Sélectionner B.mp4")).toBeChecked();
  expect(uploads).toBe(2);
});
