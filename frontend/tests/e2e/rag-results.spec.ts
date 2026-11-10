import { test, expect, type Page } from "@playwright/test";
import { resolve } from "node:path";
import { readFile } from "node:fs/promises";

const id = "22222222-2222-4222-8222-222222222222";
const video = {
  id: "camera",
  filename: "camera-parcelle.mp4",
  status: "ready",
  metadata: { duration_seconds: 6.8 },
  created_at: "2026-11-10",
};
const result = {
  status: "ready",
  observation_summary: "Un renard confirmé dans la parcelle.",
  video_count: 1,
  confirmed_species: [{ name: "renard", display_name: "Renard" }],
  predicted_species: [],
  green_space: { message: "Une mesure locale est nécessaire." },
  recommendations: [
    {
      theme: "hedges",
      title: "Piste documentaire complémentaire",
      action: "Protéger les racines pendant le chantier.",
      citation: "D1",
    },
  ],
  sources: [
    {
      citation: "D1",
      title: "Étude des haies",
      page: 2,
      original_url: "https://example.org/haies",
    },
  ],
  videos: [],
  next_steps: ["Vérifier le terrain avec un écologue."],
  limitations: ["Aucun inventaire exhaustif disponible."],
  territorial_report: {
    status: "generated",
    coverage: {
      documents_total: 2,
      documents_read: 1,
      documents_pending_review: 1,
      unreadable_ids: ["unreadable"],
      batches_rejected: [{ batch: 2, reason: "Citation non vérifiée" }],
    },
    pages: ["Diagnostic", "Aménagements", "Mise en œuvre", "Priorités"].map(
      (title, i) => ({
        title,
        paragraphs: [
          {
            text: `Texte conservé de la page ${i + 1} [D1].`,
            citations: ["D1"],
          },
        ],
      }),
    ),
    actions: [
      {
        title: "Maintenir la haie",
        action: "Conserver la continuité existante.",
        location: "En bordure de la parcelle",
        rationale: "Maintenir un corridor de déplacement.",
        conditions: "Vérifier la présence des espèces.",
        priority: "design",
        monitoring: "Observer la continuité chaque année.",
        citations: ["D1"],
      },
    ],
    ledger: [
      {
        citation: "D1",
        title: "Étude des haies",
        source_url: "https://example.org/haies",
        chunks_read: 3,
        findings: [
          {
            quote: "La haie assure une continuité.",
            page: 2,
            limits: "Résultat dépendant du contexte local.",
          },
        ],
      },
    ],
  },
};

async function setup(page: Page, territorial = true) {
  const methods: string[] = [];
  await page.addInitScript(() => {
    localStorage.setItem("symbiose:data-mode:v1", "real");
    const seeks: { time: number; duration: number }[] = [];
    Object.assign(window, { thumbnailSeeks: seeks });
    document.addEventListener(
      "seeked",
      (event) => {
        const video = event.target as HTMLVideoElement;
        if (video.closest(".video-midpoint-thumbnail"))
          seeks.push({ time: video.currentTime, duration: video.duration });
      },
      true,
    );
  });
  const dossier = {
    id: "existing-dossier",
    status: "completed",
    profile_revision: 1,
    videos: [{ video_id: video.id, filename: video.filename }],
    result: territorial
      ? result
      : {
          ...result,
          territorial_report: {
            status: "no_actionable_evidence",
            coverage: { documents_total: 1, documents_read: 1 },
            ledger: [],
          },
        },
  };
  await page.route("**/api/**", async (route) => {
    methods.push(route.request().method());
    const path = new URL(route.request().url()).pathname.replace(/^\/api/, "");
    if (path.endsWith("/file")) {
      const bytes = await readFile(resolve("src/assets/squirrel-local.mp4"));
      const range = /bytes=(\d+)-(\d*)/.exec(
        route.request().headers().range || "",
      );
      if (range) {
        const start = Number(range[1]);
        const end = range[2]
          ? Math.min(Number(range[2]), bytes.length - 1)
          : bytes.length - 1;
        return route.fulfill({
          status: 206,
          contentType: "video/mp4",
          headers: {
            "Accept-Ranges": "bytes",
            "Content-Range": `bytes ${start}-${end}/${bytes.length}`,
          },
          body: bytes.subarray(start, end + 1),
        });
      }
      return route.fulfill({
        contentType: "video/mp4",
        headers: { "Accept-Ranges": "bytes" },
        body: bytes,
      });
    }
    const values: Record<string, unknown> = {
      "/auth/me": {
        user: { id: "reader", role: "client", display_name: "Lecteur" },
        csrf_token: "token",
      },
      "/console/videos": [video],
      "/console/tasks": [],
      "/review/samples": [],
      "/review/species": [],
      "/documents": [],
      "/parcels/corpora": [
        { id, video_count: 1, latest_dossier_id: dossier.id },
      ],
      [`/parcels/corpora/${id}`]: {
        id,
        videos: dossier.videos,
        profile: {
          revision: 1,
          profile: {
            area_m2: 1000,
            land_type: "garden",
            locality: "Parcelle enregistrée",
            project_type: "park",
            details: "Conserver la haie",
          },
        },
        dossier,
      },
      "/parcels/options": {
        land_types: { garden: "Jardin" },
        project_types: { park: "Parc" },
      },
      "/parcels/videos/camera": { profile: null, dossier },
    };
    if (!(path in values))
      return route.fulfill({ status: 404, json: { detail: "Source absente" } });
    return route.fulfill({ json: values[path] });
  });
  return methods;
}

test("ouvre les vrais dossiers et toutes les sorties RAG sans écrire", async ({
  page,
}) => {
  const methods = await setup(page);
  await page.goto("/parcelles");
  await page
    .getByRole("button", {
      name: "Ouvrir le dossier Parcelle enregistrée",
      exact: true,
    })
    .click();
  await expect(page).toHaveURL(new RegExp(`/parcelles/${id}$`));
  await expect(
    page.getByRole("heading", { name: "Rapport d’aménagement du territoire" }),
  ).toBeVisible();
  await expect(page.locator(".territorial-page")).toHaveCount(4);
  await page.getByText("Maintenir la haie", { exact: true }).click();
  await expect(
    page.getByText("Conserver la continuité existante.", { exact: true }),
  ).toBeVisible();
  await page
    .getByText("Piste documentaire complémentaire · piste sourcée")
    .click();
  await expect(
    page.getByText("Protéger les racines pendant le chantier.", {
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByText("Aucun inventaire exhaustif disponible.", { exact: true }),
  ).toBeVisible();
  await page.getByText("Documents examinés et éléments de preuve (1)").click();
  await expect(
    page.getByText("La haie assure une continuité.", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", {
      name: "Ouvrir les 4 pages pour imprimer ou enregistrer en PDF",
    }),
  ).toHaveAttribute("href", /format=html$/);
  await page
    .getByText("Toutes les sorties du dossier (JSON)", { exact: true })
    .click();
  await expect(page.locator(".dossier-audit pre")).toContainText(
    "Citation non vérifiée",
  );
  await expect(
    page.getByRole("button", { name: "Actualiser mon dossier" }),
  ).toBeEnabled();
  await page.screenshot({
    path: "test-results/rag-reader.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(391);
  await expect(
    page.getByRole("heading", { name: "Rapport d’aménagement du territoire" }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/rag-reader-mobile.png",
    fullPage: true,
  });
  expect(methods.every((method) => method === "GET")).toBe(true);
});

test("affiche le RAG réel sur l’accueil sans score inventé et ouvre les dossiers vidéo", async ({
  page,
}) => {
  await setup(page);
  await page.goto("/");
  await expect(page.locator(".sym-diagnostic")).toHaveCount(0);
  await expect(page.locator(".sym-recommendation h3")).toHaveText(
    "Maintenir la haie",
  );
  await page
    .getByRole("link", { name: "Lire le dossier : Maintenir la haie" })
    .click();
  await expect(page).toHaveURL(new RegExp(`/parcelles/${id}$`));
  await page.goto("/videos/camera/dossier");
  await expect(
    page.getByRole("heading", { name: "Votre dossier biodiversité" }),
  ).toBeVisible();
  await expect(page.locator(".territorial-page")).toHaveCount(4);
  await expect(
    page.getByRole("button", { name: "Préparer mon dossier" }),
  ).toHaveCount(0);
});

test("conserve les pistes sourcées quand la génération territoriale est insuffisante", async ({
  page,
}) => {
  await setup(page, false);
  await page.goto(`/parcelles/${id}`);
  await page
    .getByText("Piste documentaire complémentaire · piste sourcée")
    .click();
  await expect(
    page.getByText("Protéger les racines pendant le chantier.", {
      exact: true,
    }),
  ).toBeVisible();
});

test("la vidéothèque extrait une vraie image à mi-durée", async ({ page }) => {
  await setup(page);
  await page.goto("/videos");
  const thumbnail = page.locator(".sv-real-thumbnail img");
  await expect(thumbnail).toHaveAttribute("src", /^data:image\/jpeg;base64,/, {
    timeout: 20000,
  });
  const seeks = await page.evaluate(
    () =>
      (
        window as unknown as {
          thumbnailSeeks: { time: number; duration: number }[];
        }
      ).thumbnailSeeks,
  );
  expect(seeks.length).toBeGreaterThan(0);
  expect(
    seeks.some((seek) => Math.abs(seek.time - seek.duration / 2) < 0.05),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/video-midpoint.png",
    fullPage: true,
  });
});
