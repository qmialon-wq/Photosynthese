import { test, expect, type Page } from "@playwright/test";

// Contrats HTTP simulés uniquement dans ce fichier de test. Aucun mode démo dans l'app.
const id = "11111111-1111-4111-8111-111111111111";
const sampleId = "sample-one";
const classes = [
  "chevreuil",
  "sanglier",
  "buse",
  "pigeons",
  "martres",
  "renards",
  "blaireaux",
  "chouette",
  "geai",
  "faisans",
];
async function identify(page: Page) {
  await page.addInitScript(() =>
    localStorage.setItem("biosentinelle-reviewer", "alice"),
  );
}
test("annotation corrigée persistante après rechargement", async ({ page }) => {
  await identify(page);
  let sample = {
    id: sampleId,
    video_id: "video",
    original_name: "terrain.mp4",
    revision: 0,
    state: "pending",
    label: null as string | null,
    predicted_label: null,
    species_candidate: "chevreuil",
    box: { x: 0.1, y: 0.1, w: 0.5, h: 0.5 },
    original_box: { x: 0.1, y: 0.1, w: 0.5, h: 0.5 },
    split: "train",
    test_locked: false,
    render_status: "ready",
    quality: {},
    frame_quality: {},
    actor: "alice",
    created_at: new Date().toISOString(),
    provenance: {},
    detection_score: 0.9,
    classification_score: null,
  };
  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url()),
      path = url.pathname;
    if (path.endsWith("/review/species"))
      return route.fulfill({
        json: classes.map((name, class_index) => ({ name, class_index })),
      });
    if (path.includes("/decisions")) {
      const body = route.request().postDataJSON();
      expect(body.expected_revision).toBe(sample.revision);
      sample = {
        ...sample,
        label: body.label,
        box: body.box,
        state: "corrected",
        revision: 1,
      };
      return route.fulfill({ json: sample });
    }
    if (path.endsWith("/history")) return route.fulfill({ json: [sample] });
    if (path.includes("/images/"))
      return route.fulfill({
        contentType: "image/svg+xml",
        body: '<svg xmlns="http://www.w3.org/2000/svg" width="500" height="300"><rect width="500" height="300" fill="#b8cbb0"/></svg>',
      });
    if (path.endsWith("/review/samples"))
      return route.fulfill({
        json: url.searchParams.get("state") === sample.state ? [sample] : [],
      });
    return route.fulfill({ json: [] });
  });
  await page.goto("/review");
  await page.getByRole("button", { name: /Revoir terrain/ }).click();
  await page.getByLabel("Espèce confirmée").selectOption("renards");
  await page.getByRole("spinbutton", { name: "X", exact: true }).fill("0.2");
  // Le commentaire est facultatif, y compris lors d'une correction de boîte.
  await page.getByRole("button", { name: "Confirmer l’annotation" }).click();
  await expect(
    page.getByRole("status").filter({ hasText: "Décision enregistrée" }),
  ).toBeVisible();
  await page.reload();
  await page.getByLabel("État de validation").selectOption("corrected");
  await page.getByRole("button", { name: /Revoir terrain/ }).click();
  await expect(page.getByLabel("Espèce confirmée")).toHaveValue("renards");
  await expect(
    page.getByRole("spinbutton", { name: "X", exact: true }),
  ).toHaveValue("0.2");
});

test("import, analyse asynchrone et téléchargement JSON", async ({ page }) => {
  await identify(page);
  let kind = "import_upload",
    analysisStarted = false;
  const video = {
    id: "video",
    filename: "terrain.mp4",
    species_candidate: "chevreuil",
    status: "ready",
    metadata: { duration_seconds: 3 },
    created_at: new Date().toISOString(),
  };
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/uploads"))
      return route.fulfill({ json: { id, chunk_size: 4194304 } });
    if (path.includes("/chunks/")) return route.fulfill({ json: { size: 4 } });
    if (path.endsWith("/complete"))
      return route.fulfill({ json: { id, status: "queued" } });
    if (path.endsWith("/analyze")) {
      analysisStarted = true;
      kind = "analysis";
      return route.fulfill({ json: { id, status: "queued" } });
    }
    if (path.endsWith(`/tasks/${id}`))
      return route.fulfill({
        json: {
          id,
          kind,
          status: "completed",
          request: { video_id: "video" },
          progress: {},
          result: { video_id: "video", output: "test" },
          cancel_requested: false,
        },
      });
    if (path.endsWith("/artifacts/report"))
      return route.fulfill({
        json: {
          status: "no_detection",
          frames_decoded: 12,
          detections: 0,
          frames: [],
          diagnostics: { gpu_elapsed_seconds: null },
          species: [],
        },
      });
    if (path.endsWith("/videos/video")) return route.fulfill({ json: video });
    if (path.endsWith("/videos")) return route.fulfill({ json: [video] });
    return route.fulfill({ json: [] });
  });
  await page.goto("/videos");
  await page
    .getByLabel("Importer une ou plusieurs vidéos", { exact: true })
    .setInputFiles({
      name: "terrain.mp4",
      mimeType: "video/mp4",
      buffer: Buffer.from("test"),
    });
  await expect(
    page.getByRole("heading", { name: "Configurer l’analyse" }),
  ).toBeVisible();
  // This existing scenario intentionally covers video-only analysis.
  await page.getByLabel("Recevoir mon dossier biodiversité").uncheck();
  await page
    .getByRole("button", { name: "Lancer l’analyse", exact: true })
    .click();
  await expect(
    page.getByText(
      "Aucun animal détecté sur les images analysées. Le résultat est valide.",
    ),
  ).toBeVisible();
  expect(analysisStarted).toBe(true);
  await expect(
    page.getByRole("link", { name: /Rapport JSON/ }),
  ).toHaveAttribute("href", `/api/console/tasks/${id}/artifacts/report`);
});

test("soumettre un entraînement, voir sa progression et demander son arrêt", async ({
  page,
}) => {
  await identify(page);
  let started = false,
    cancelled = false;
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/console/training") {
      started = true;
      return route.fulfill({ json: { id, status: "queued" } });
    }
    if (path.endsWith("/cancel")) {
      cancelled = true;
      return route.fulfill({ json: { cancel_requested: true } });
    }
    if (path.endsWith(`/tasks/${id}`))
      return route.fulfill({
        json: {
          id,
          kind: "training",
          status: "running",
          request: { model_name: "tf_efficientnetv2_b0" },
          progress: { stage: "head", current: 1, total: 6 },
          cancel_requested: cancelled,
        },
      });
    if (path === "/api/console/tasks")
      return route.fulfill({
        json: started
          ? [
              {
                id,
                kind: "training",
                status: "running",
                request: { model_name: "tf_efficientnetv2_b0" },
                created_at: new Date().toISOString(),
              },
            ]
          : [],
      });
    if (path.endsWith("/console/training/datasets"))
      return route.fulfill({
        json: [
          {
            id: "a".repeat(64),
            name: "dataset-validé",
            source: "review",
            ready: true,
          },
        ],
      });
    if (path.endsWith("/metrics"))
      return route.fulfill({
        json: [
          {
            event_key: "head:1",
            metrics: {
              phase: "head",
              epoch: 1,
              train_loss: 0.4,
              validation: { accuracy: 0.8, macro_f1: 0.7 },
            },
          },
        ],
      });
    return route.fulfill({ json: [] });
  });
  await page.goto("/training");
  await page.getByLabel("Dataset d’entraînement").selectOption("a".repeat(64));
  await page.getByRole("button", { name: "Démarrer l’entraînement" }).click();
  await expect(page.getByText("1 / 6", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Demander l’arrêt" }).click();
  await expect(
    page.getByText("Arrêt demandé, en attente d’un point d’interruption sûr."),
  ).toBeVisible();
  expect(cancelled).toBe(true);
});

test("métriques réelles du registre et navigation mobile", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route("**/api/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    return route.fulfill({
      json: path.endsWith("/models")
        ? [
            {
              id,
              name: "Modèle de test",
              metrics: {
                validation: {
                  accuracy: 0.75,
                  macro_f1: 0.6,
                  count: 4,
                  classes: ["chevreuil", "renards"],
                  confusion_matrix: [
                    [2, 1],
                    [0, 1],
                  ],
                },
              },
              metadata: { model_name: "test-only" },
              active: false,
            },
          ]
        : [],
    });
  });
  await page.goto(`/evaluation?model=${id}`);
  await expect(page.getByText("75.0 %", { exact: true })).toBeVisible();
  await expect(page.getByRole("table")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "Menu de navigation" }).click();
  await page
    .getByRole("link", { name: "Espace observation", exact: true })
    .click();
  await page.getByRole("button", { name: "Menu de navigation" }).click();
  await page.getByRole("link", { name: "Vidéothèque", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Vidéothèque", exact: true }),
  ).toBeVisible();
});
