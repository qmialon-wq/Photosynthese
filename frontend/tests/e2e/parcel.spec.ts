import { mockApi } from "./mock-api";
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("parcelle, analyse, dossier téléchargeable et persistance après rechargement", async ({
  page,
}) => {
  const analysis = "11111111-1111-4111-8111-111111111111";
  let saved: Record<string, unknown> | null = null;
  let started = false;
  const video = {
    id: "v",
    filename: "parcelle.mp4",
    metadata: {},
    species_candidate: null,
  };
  const result = {
    status: "insufficient_sources",
    observation_summary: "Aucun animal détecté sur les images analysées.",
    confirmed_species: [],
    predicted_species: [],
    recommendations: [],
    sources: [],
    next_steps: [],
    limitations: [],
    green_space: {
      message: "Aucun pourcentage justifié par les sources disponibles.",
    },
  };
  await mockApi(page, async (route) => {
    const request = route.request(),
      path = new URL(request.url()).pathname;
    let response: unknown = [];
    if (path.endsWith("/parcels/options"))
      response = {
        land_types: { pasture: "Pâturage", woodland: "Bois" },
        project_types: { housing: "Habitation", park: "Parc ou jardin" },
      };
    else if (path.endsWith("/parcels/videos/v")) {
      if (request.method() === "PUT") {
        saved = request.postDataJSON();
        response = { revision: 1, profile: saved };
      } else
        response = {
          profile: saved ? { revision: 1, profile: saved } : null,
          dossier: started
            ? {
                id: "dossier",
                status: "completed",
                profile_revision: 1,
                result,
              }
            : null,
        };
    } else if (path.endsWith("/console/videos/v")) response = video;
    else if (path.endsWith("/analyze")) {
      expect(request.postDataJSON().parcel_revision).toBe(1);
      started = true;
      response = { id: analysis, status: "queued" };
    } else if (path.endsWith(`/tasks/${analysis}`))
      response = {
        id: analysis,
        kind: "analysis",
        status: "completed",
        request: { video_id: "v" },
        result: {},
        progress: {},
      };
    else if (path.endsWith("/artifacts/report"))
      response = {
        frames: [],
        frames_decoded: 10,
        detections: 0,
        diagnostics: {},
        species: [],
      };
    await route.fulfill({ json: response });
  });
  await page.goto("/analyses?video=v");
  await page.getByLabel("Surface de la parcelle (m²)").fill("2500");
  await page
    .getByRole("combobox", { name: "Type de parcelle", exact: true })
    .selectOption("pasture");
  await page
    .getByRole("combobox", { name: "Projet souhaité", exact: true })
    .selectOption("housing");
  await page.getByLabel("Commune ou secteur (facultatif)").fill("Caen");
  await page
    .getByRole("button", { name: "Lancer l’analyse", exact: true })
    .click();
  await expect(
    page.getByRole("link", { name: "Télécharger mon dossier (.txt)" }),
  ).toHaveAttribute("href", "/api/parcels/dossiers/dossier/export");
  await expect(
    page.getByRole("heading", { name: "Vidéo annotée", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText(/Les sources validées sont insuffisantes/),
  ).toBeVisible();
  const scan = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(
    scan.violations.map((v) => ({
      id: v.id,
      nodes: v.nodes.map((n) => n.target),
    })),
  ).toEqual([]);
  await page.reload();
  await expect(page.getByLabel("Surface de la parcelle (m²)")).toHaveValue(
    "2500",
  );
  await expect(
    page.getByRole("link", { name: "Télécharger mon dossier (.txt)" }),
  ).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});
