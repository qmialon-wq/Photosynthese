import {
  openDisplaySettings,
  closeDisplaySettings,
  selectSource,
  expectSource,
} from "./display-settings";
import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";

const routes = [
  "/",
  "/videos",
  "/parcelles",
  "/analyses",
  "/review",
  "/documents",
];
const session = {
  user: {
    id: "test-reader",
    email: null,
    role: "client",
    display_name: "Lecteur de test",
    created_at: "2026-01-01",
    deleted_at: null,
  },
  csrf_token: "test",
};
const video = {
  id: "recorded-video",
  filename: "camera-enregistree.mp4",
  status: "ready",
  species_candidate: null,
  created_at: "2026-11-01",
  metadata: { duration_seconds: 6.8, width: 1080, height: 1920 },
};
const sample = {
  id: "recorded-sample",
  video_id: video.id,
  original_name: video.filename,
  frame_index: 12,
  state: "validated",
  label: "renard",
  predicted_label: "renard",
  test_locked: false,
  quality: null,
  frame_quality: {},
  box: { x: 0, y: 0, w: 1, h: 1 },
};
const task = {
  id: "recorded-analysis",
  kind: "analysis",
  status: "completed",
  request: { video_id: video.id },
  created_at: "2026-11-01",
  result: { video_id: video.id },
};
const document = {
  id: "recorded-document",
  title: "Titre transmis par l’API de test",
  published_date: null,
  url: "https://example.org/publication",
  species_links: [{ species: "renard" }],
  status: "indexed",
};
const corpus = {
  id: "recorded-corpus",
  video_count: 1,
  latest_dossier_id: null,
};
const detail = {
  id: corpus.id,
  videos: [{ video_id: video.id, filename: video.filename }],
  profile: { profile: { locality: "Bois enregistré", project_type: "park" } },
  dossier: null,
};
const picker = (page: Page) =>
  page.getByLabel("Source de données", { exact: true });
async function navigate(page: Page, path: string) {
  await page.locator(`.sym-wheel-link[data-section="${path}"]`).click();
  await expect(page.locator(".sym-wheel-link.is-active")).toHaveAttribute(
    "data-section",
    path,
  );
}
async function apiFixture(
  page: Page,
  options: {
    empty?: boolean;
    overrides?: Record<string, number>;
    delay?: number;
  } = {},
) {
  const methods: string[] = [],
    paths: string[] = [];
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname.replace(/^\/api/, "");
    methods.push(route.request().method());
    paths.push(path);
    if (options.delay)
      await new Promise((resolve) => setTimeout(resolve, options.delay));
    const failure = options.overrides?.[path];
    if (failure)
      return route
        .fulfill({
          status: failure,
          json: { detail: "Source de test indisponible" },
        })
        .catch(() => {});
    if (path.endsWith("/file") || path.endsWith("/artifacts/video"))
      return route
        .fulfill({
          path: resolve("src/assets/squirrel-local.mp4"),
          contentType: "video/mp4",
        })
        .catch(() => {});
    if (path.endsWith("/images/original"))
      return route
        .fulfill({
          path: resolve("src/assets/analysis-deer.png"),
          contentType: "image/png",
        })
        .catch(() => {});
    const values: Record<string, unknown> = {
      "/auth/me": session,
      "/auth/status": { setup_required: false },
      "/console/videos": options.empty ? [] : [video],
      "/review/samples": options.empty ? [] : [sample],
      "/console/tasks": options.empty ? [] : [task],
      "/review/species": [{ name: "renard" }],
      "/parcels/corpora": options.empty ? [] : [corpus],
      "/parcels/corpora/recorded-corpus": detail,
      "/parcels/corpora/recorded-corpus/territorial-context": {
        location: null,
        profile: detail.profile.profile,
        profile_revision: 0,
        query: null,
      },
      "/parcels/options": { land_types: {}, project_types: {} },
      "/documents": options.empty ? [] : [document],
      "/console/tasks/recorded-analysis/artifacts/report": {
        frames: [
          {
            frame_index: 12,
            time_seconds: 1.2,
            detections: [
              {
                box: { x: 0.1, y: 0.2, w: 0.3, h: 0.4 },
                classification: { label: "renard", score: 0.82 },
              },
            ],
          },
        ],
      },
    };
    if (!(path in values)) throw new Error(`Appel API inattendu : ${path}`);
    return route.fulfill({ json: values[path] }).catch(() => {});
  });
  return { methods, paths };
}
test.use({ viewport: { width: 1600, height: 900 } });

test("A — démonstration autonome, données cohérentes et simulations sans API", async ({
  page,
}) => {
  const calls: string[] = [];
  page.on("request", (request) => {
    if (new URL(request.url()).pathname.startsWith("/api"))
      calls.push(request.url());
  });
  await page.goto("/");
  await expect(page.locator(".sym-demo-note")).toHaveText(
    "Mode démonstration · données fictives",
  );
  await expect(page.locator(".sym-stat strong")).toHaveText([
    "12",
    "8",
    "2",
    "4",
  ]);
  await navigate(page, "/videos");
  await expect(page.locator(".sym-stat strong")).toHaveText([
    "248",
    "125 min",
    "12",
  ]);
  await expect(page.locator(".sv-video-card")).toHaveCount(4);
  await navigate(page, "/parcelles");
  await expect(page.locator(".sf-project-card")).toHaveCount(6);
  await navigate(page, "/analyses");
  await expect(page.locator("#sa-filename")).toHaveText("VID_00124.mp4");
  await page
    .getByRole("button", { name: "Lancer l’analyse", exact: true })
    .click();
  await expect(page.locator(".sa-analysis-completed")).toBeVisible();
  await navigate(page, "/review");
  await expect(page.locator(".sr-observation")).toHaveCount(8);
  await navigate(page, "/documents");
  await page
    .getByLabel("Espèce du corpus", { exact: true })
    .selectOption("chevreuil");
  await expect(page.locator(".sd-document-card")).toHaveCount(5);
  expect(calls).toEqual([]);
});

test("B — les six rubriques lisent exclusivement les réponses réelles et désactivent les écritures", async ({
  page,
}) => {
  const api = await apiFixture(page);
  await page.goto("/");
  await selectSource(page, "real");
  await expect(page.locator(".sym-stat strong")).toHaveText([
    "1",
    "1",
    "1",
    "0",
  ]);
  await expect(page.locator(".sym-diagnostic")).toHaveCount(0);
  await expect(page.locator(".sym-recommendation")).not.toContainText(
    "Maintenir et renforcer",
  );
  await navigate(page, "/videos");
  await expect(page.locator(".sv-video-card")).toHaveCount(1);
  await expect(page.locator(".sv-video-card")).toContainText(video.filename);
  await expect(
    page.getByRole("button", { name: "Importer des vidéos", exact: true }),
  ).toBeDisabled();
  await expect(page.locator(".sv-thumbnail")).toHaveClass(
    /sym-thumbnail-empty/,
  );
  await navigate(page, "/parcelles");
  await expect(page.locator(".sf-project-card")).toHaveCount(1);
  await expect(page.locator(".sf-project-card")).toContainText(
    "Bois enregistré",
  );
  await page
    .getByRole("button", {
      name: "Ouvrir le dossier Bois enregistré",
      exact: true,
    })
    .click();
  await expect(page).toHaveURL(/\/parcelles\/recorded-corpus$/);
  await expect(
    page.getByText("Aucun dossier n’a encore été généré pour cette parcelle."),
  ).toBeVisible();
  await navigate(page, "/analyses");
  await expect(page.locator("#sa-filename")).toHaveText(video.filename);
  await expect(
    page.getByRole("button", { name: "Lancer l’analyse", exact: true }),
  ).toBeDisabled();
  await expect(page.locator(".sym-report-list")).toContainText(
    "1.2 s · renard · 82.0 %",
  );
  await expect(page.locator(".sa-player-demo")).not.toContainText("SIMULÉE");
  await navigate(page, "/review");
  await expect(page.locator(".sr-observation")).toHaveCount(1);
  await page
    .getByRole("checkbox", {
      name: "Sélectionner l’observation 1",
      exact: true,
    })
    .check();
  await expect(
    page.getByRole("button", { name: "Valider la sélection", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Effacer la sélection", exact: true }),
  ).toBeDisabled();
  await navigate(page, "/documents");
  await expect(page.locator(".sd-document-card")).toHaveCount(1);
  await expect(page.locator(".sd-document-card")).toContainText(document.title);
  await expect(page.locator(".sd-document-card")).not.toContainText("fictive");
  await expect(
    page.getByRole("button", { name: "Importer un document", exact: true }),
  ).toBeDisabled();
  await page
    .getByRole("button", { name: `Consulter ${document.title}`, exact: true })
    .click();
  await expect(
    page.getByRole("link", {
      name: "Consulter la source originale",
      exact: true,
    }),
  ).toHaveAttribute("href", document.url);
  expect(api.paths).toContain(
    "/console/tasks/recorded-analysis/artifacts/report",
  );
  expect(new Set(api.methods)).toEqual(new Set(["GET"]));
});

test("B — états vides, source absente et erreur sans données de remplacement", async ({
  page,
}) => {
  const api = await apiFixture(page, {
    empty: true,
    overrides: { "/review/samples": 403, "/documents": 503 },
  });
  await page.goto("/videos");
  await selectSource(page, "real");
  await expect(
    page.getByText("Aucune vidéo disponible.", { exact: true }),
  ).toBeVisible();
  await expect(page.locator(".sv-video-card")).toHaveCount(0);
  await navigate(page, "/parcelles");
  await expect(
    page.getByText("Aucun dossier enregistré.", { exact: true }),
  ).toBeVisible();
  await navigate(page, "/analyses");
  await expect(
    page.getByText("Aucune analyse enregistrée.", { exact: true }),
  ).toBeVisible();
  await expect(page.locator(".sa-player")).toHaveCount(0);
  await navigate(page, "/review");
  await expect(page.getByRole("alert")).toContainText("Accès non autorisé");
  await navigate(page, "/documents");
  await expect(
    page
      .getByRole("status")
      .filter({ hasText: "Fonctionnalité non connectée" }),
  ).toBeVisible();
  await expect(page.locator(".sd-document-card")).toHaveCount(0);
  expect(new Set(api.methods)).toEqual(new Set(["GET"]));
});

test("B — l’authentification est requise avant toute lecture métier", async ({
  page,
}) => {
  const api = await apiFixture(page, { overrides: { "/auth/me": 401 } });
  await page.goto("/videos");
  await selectSource(page, "real");
  await expect(page.getByRole("alert")).toContainText("Connexion requise");
  await expect(page.locator(".sv-video-card")).toHaveCount(0);
  // The gear verifies the administrative link; switching to real data verifies
  // authentication independently before any business endpoint can be read.
  expect(api.paths).toEqual(["/auth/me", "/auth/me"]);
});

test("C — basculement sans rotation, sélection réinitialisée et réponse tardive ignorée", async ({
  page,
}) => {
  await apiFixture(page, { delay: 300 });
  await page.goto("/videos");
  await page.locator(".sv-video-card input[type=checkbox]").first().check();
  await page
    .locator(".sym-wheel")
    .evaluate((el) => el.setAttribute("data-instance", "original"));
  const arc = await page.locator(".sym-wheel-arc path").getAttribute("d");
  for (let i = 0; i < 3; i++) {
    await selectSource(page, "real");
    await expect(page).toHaveURL(/\/videos$/);
    await expect(page.locator(".sv-video-card")).toHaveCount(0);
    await selectSource(page, "demo");
    await expect(page.locator(".sv-video-card")).toHaveCount(4);
    await expect(
      page.locator(".sv-video-card input[type=checkbox]").first(),
    ).not.toBeChecked();
  }
  await page.waitForTimeout(700); // Laisser arriver les réponses volontairement retardées.
  await expect(page.locator(".sv-video-card").first()).toContainText(
    "VID_00124.mp4",
  );
  await expect(page.locator(".sym-wheel")).toHaveAttribute(
    "data-instance",
    "original",
  );
  expect(await page.locator(".sym-wheel-arc path").getAttribute("d")).toBe(arc);
  await expect(page.locator(".sym-wheel-link.is-active")).toHaveAttribute(
    "data-section",
    "/videos",
  );
});

test("C — changement de mode pendant une analyse et conservation des changements locaux entre rubriques", async ({
  page,
}) => {
  await apiFixture(page);
  await page.goto("/analyses");
  await page
    .getByRole("button", { name: "Lancer l’analyse", exact: true })
    .click();
  await selectSource(page, "real");
  await expect(page.locator(".sa-analysis-status progress")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Lancer l’analyse", exact: true }),
  ).toBeDisabled();
  await selectSource(page, "demo");
  await expect(page.locator(".sa-analysis-completed")).toHaveCount(0);
  await navigate(page, "/documents");
  await page
    .getByLabel("Espèce du corpus", { exact: true })
    .selectOption("chevreuil");
  await page
    .getByLabel("Documents par page", { exact: true })
    .selectOption("4");
  await page
    .getByRole("checkbox", {
      name: "Tout sélectionner sur cette page",
      exact: true,
    })
    .check();
  await page
    .getByRole("button", { name: "Retirer du corpus", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Confirmer le retrait simulé", exact: true })
    .click();
  await navigate(page, "/");
  await navigate(page, "/documents");
  await page
    .getByLabel("Espèce du corpus", { exact: true })
    .selectOption("chevreuil");
  await expect(page.getByLabel("Espèce du corpus")).toContainText(
    "Chevreuil · 1 document",
  );
});

test("D — persistance du mode après navigation et rechargement, sans sélecteur sur Connexion", async ({
  page,
}) => {
  await apiFixture(page);
  await page.goto("/videos");
  await selectSource(page, "real");
  await expect(page.locator(".sv-video-card")).toHaveCount(1);
  await navigate(page, "/documents");
  await page.reload();
  await expectSource(page, "real");
  await expect(page.locator(".sd-document-card")).toHaveCount(1);
  await page.goto("/connexion");
  await expect(
    page.getByRole("heading", { name: "Connexion", exact: true }),
  ).toBeVisible();
  await expect(picker(page)).toHaveCount(0);
});

test("E — captures des douze vues et cadre commun à 1600 × 900", async ({
  page,
}) => {
  test.setTimeout(150000);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await apiFixture(page);
  const directory = resolve("../output/symbiose/etape-8");
  await mkdir(directory, { recursive: true });
  await page.goto("/");
  const wheel = () =>
    page.locator(".sym-wheel").evaluate((el) => ({
      html: el.querySelector("svg")!.outerHTML,
      width: el.getBoundingClientRect().width,
      height: el.getBoundingClientRect().height,
    }));
  const baseline = await wheel();
  for (const mode of ["demo", "real"] as const) {
    await selectSource(page, mode);
    for (let index = 0; index < routes.length; index++) {
      await navigate(page, routes[index]);
      await expect(
        page.locator(".sym-source-state[aria-busy=true]"),
      ).toHaveCount(0);
      await page.evaluate(async () => {
        await document.fonts.ready;
        await Promise.all(
          [...document.images].map((img) => img.decode().catch(() => {})),
        );
      });
      await expect
        .poll(() =>
          page
            .locator(".sr-observation-preview video")
            .evaluateAll((elements) =>
              elements.every(
                (el) =>
                  (el as HTMLVideoElement).readyState >= 2 &&
                  !(el as HTMLVideoElement).seeking,
              ),
            ),
        )
        .toBe(true);
      expect(await wheel()).toEqual(baseline);
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
      await page.mouse.move(0, 0);
      await page.screenshot({
        path: resolve(
          directory,
          `${mode === "real" ? "api-test" : mode}-${index + 1}-1600x900.png`,
        ),
      });
    }
  }
  const scan = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(scan.violations).toEqual([]);
});

test("E — sélecteur mobile accessible sans déplacement des commandes du compte", async ({
  page,
}) => {
  await apiFixture(page, { empty: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/videos");
  await openDisplaySettings(page);
  await expect(picker(page)).toBeInViewport();
  await closeDisplaySettings(page);
  const actions = await page
    .locator(".sym-header-actions button")
    .evaluateAll((elements) =>
      elements.map((el) => el.getBoundingClientRect().toJSON()),
    );
  await selectSource(page, "real");
  await expect(
    page.getByText("Aucune vidéo disponible.", { exact: true }),
  ).toBeVisible();
  expect(
    await page
      .locator(".sym-header-actions button")
      .evaluateAll((elements) =>
        elements.map((el) => el.getBoundingClientRect().toJSON()),
      ),
  ).toEqual(actions);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await openDisplaySettings(page);
  await picker(page).focus();
  await page.keyboard.press("ArrowUp");
  await expect(picker(page)).toBeFocused();
});
