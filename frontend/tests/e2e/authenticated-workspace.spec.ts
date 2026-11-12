import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const video = {
  id: "field-video",
  filename: "terrain.mp4",
  species_candidate: null,
  status: "ready",
  metadata: {},
  created_at: "2026-11-12T08:00:00Z",
};
const sample = {
  id: "field-sample",
  video_id: video.id,
  original_name: video.filename,
  frame_index: 1,
  revision: 2,
  state: "pending",
  label: null,
  predicted_label: null,
  species_candidate: null,
  test_locked: false,
  render_status: "ready",
  split: "train",
  quality: {},
  frame_quality: {},
  box: { x: 0.1, y: 0.1, w: 0.5, h: 0.5 },
  original_box: { x: 0.1, y: 0.1, w: 0.5, h: 0.5 },
};

async function fixture(page: Page, role: "client" | "admin" | null) {
  // Reproduit un navigateur ayant conservé l'ancien choix démo.
  await page.addInitScript(() =>
    localStorage.setItem("symbiose:data-mode:v1", "demo"),
  );
  const writes: { path: string; body: any }[] = [];
  const reads: string[] = [];
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname.replace(/^\/api/, "");
    const reply = (json: unknown, status = 200) =>
      route.fulfill({ status, json });
    if (path === "/auth/me")
      return role
        ? reply({
            user: {
              id: "owner",
              email: "owner@example.test",
              display_name: "Camille",
              role,
              created_at: "2026-11-12",
              deleted_at: null,
            },
            csrf_token: "session-csrf",
          })
        : reply({ detail: "Connexion requise" }, 401);
    if (path === "/auth/status") return reply({ setup_required: false });
    if (!["GET", "HEAD"].includes(request.method())) {
      expect(request.headers()["x-csrf-token"]).toBe("session-csrf");
      const body = request.postDataJSON();
      writes.push({ path, body });
      if (path.endsWith("/analyze")) return reply({ id: "analysis-task" }, 202);
      if (path.endsWith("/prepare-review"))
        return reply({ id: "review-task" }, 202);
      if (path === "/review/samples/batch-decisions")
        return reply({ updated: 1, conflicts: [] });
      return reply({});
    }
    reads.push(path);
    if (path === "/console/videos") return reply([video]);
    if (path === `/console/videos/${video.id}`) return reply(video);
    if (path === "/console/models") return reply([]);
    if (path === "/parcels/options")
      return reply({ land_types: {}, project_types: {} });
    if (path === `/parcels/videos/${video.id}`)
      return reply({ profile: null, dossier: null });
    if (path === "/review/samples") return reply([sample]);
    if (["/review/species", "/documents/species"].includes(path))
      return reply([
        { name: "chevreuil", display_name: "Chevreuil", class_index: 0 },
      ]);
    if (path.includes("/images/"))
      return route.fulfill({
        contentType: "image/svg+xml",
        body: '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300"><rect width="400" height="300" fill="#56754d"/></svg>',
      });
    if (path === "/console/dashboard")
      return reply({
        counts: { videos: 1, species: 0, pending: 1, tasks: 0 },
        distribution: [],
        latest_training: null,
      });
    if (
      path === "/console/tasks/analysis-task" ||
      path === "/console/tasks/review-task"
    )
      return reply({
        id: path.split("/").at(-1),
        kind: path.includes("review-task") ? "prepare_review" : "analysis",
        status: "queued",
        progress: {},
        request: { video_id: video.id },
        result: null,
        error: null,
      });
    return reply([]);
  });
  return { writes, reads };
}

test("landing publique sans données fictives, accessible et adaptée au mobile", async ({
  page,
}) => {
  const { reads } = await fixture(page, null);
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "biodiversité",
  );
  await expect(
    page.getByRole("link", { name: "Commencer mes observations" }),
  ).toHaveAttribute("href", "/inscription");
  await expect(
    page.getByText(/démonstration|données fictives|lecture seule/i),
  ).toHaveCount(0);
  expect(reads).toEqual([]);
  expect(
    (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze())
      .violations,
  ).toEqual([]);
  await page.screenshot({
    path: "test-results/landing-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/landing-mobile.png",
    fullPage: true,
  });
});

test("les pages de travail exigent une session", async ({ page }) => {
  const { reads } = await fixture(page, null);
  for (const path of [
    "/videos",
    "/analyses",
    "/review",
    "/documents",
    "/parcelles",
    "/profil",
    "/admin",
  ]) {
    await page.goto(path);
    await expect(page).toHaveURL(/\/connexion$/);
  }
  expect(reads).toEqual([]);
});

for (const role of ["client", "admin"] as const) {
  test(`${role} : Accueil ouvre le module connecté, la landing revient après déconnexion`, async ({
    page,
  }) => {
    await fixture(page, role);
    let connected = true;
    await page.route("**/api/auth/me", (route) =>
      route.fulfill(
        connected
          ? {
              json: {
                user: {
                  id: "owner",
                  role,
                  display_name: "Camille",
                  email: null,
                  created_at: "2026-11-12",
                  deleted_at: null,
                },
                csrf_token: "session-csrf",
              },
            }
          : { status: 401, json: { detail: "Connexion requise" } },
      ),
    );
    await page.route("**/api/auth/logout", (route) => {
      expect(route.request().headers()["x-csrf-token"]).toBe("session-csrf");
      connected = false;
      return route.fulfill({ status: 204 });
    });
    await page.route("**/api/console/tasks?*", (route) =>
      route.fulfill({
        json: [
          {
            id: "saved-analysis",
            kind: "analysis",
            status: "queued",
            request: { video_id: video.id },
            created_at: "2026-11-12T08:00:00Z",
          },
        ],
      }),
    );
    await page.goto("/");
    const home = page.getByRole("heading", {
      level: 1,
      name: "Vos observations, simplement.",
    });
    await expect(home).toBeVisible();
    await expect(
      page.getByRole("link", { name: /Analyse vidéo · saved-an/ }),
    ).toHaveAttribute("href", /task=saved-analysis/);
    await expect(page.locator(".landing")).toHaveCount(0);
    await page.reload();
    await expect(home).toBeVisible();
    await page.locator('.sym-wheel-link[data-section="/videos"]').click();
    await page.locator('.sym-wheel-link[data-section="/"]').click();
    await expect(home).toBeVisible();
    await expect(
      page.locator('.sym-wheel-link[data-section="/"]'),
    ).toHaveAttribute("aria-current", "page");
    await page
      .getByRole("link", { name: "Symbiose Normandie — accueil", exact: true })
      .click();
    await expect(home).toBeVisible();
    await page.getByRole("button", { name: "Mon profil", exact: true }).click();
    await page
      .getByRole("button", { name: "Se déconnecter", exact: true })
      .click();
    await page.goto("/");
    await expect(page.locator(".landing")).toBeVisible();
    await expect(home).toHaveCount(0);
    await page.reload();
    await expect(page.locator(".landing")).toBeVisible();
  });

  test(`${role} : restauration de session et accès aux pages métier`, async ({
    page,
  }) => {
    await fixture(page, role);
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    for (const [path, title] of [
      ["/videos", "Vidéothèque"],
      ["/parcelles", "Mes dossiers"],
      ["/analyses", "Analyse vidéo"],
      ["/review", "Validation humaine"],
      ["/documents", "Documents scientifiques"],
    ]) {
      await page.goto(path);
      await expect(
        page.getByRole("heading", { level: 1, name: title, exact: true }),
      ).toBeVisible();
      await expect(
        page.getByText(/Mode démonstration|Données réelles · lecture seule/),
      ).toHaveCount(0);
      if (["/analyses", "/review", "/documents"].includes(path)) {
        expect(
          (
            await new AxeBuilder({ page })
              .include(".sym-main")
              .withTags(["wcag2a", "wcag2aa"])
              .analyze()
          ).violations,
        ).toEqual([]);
      }
    }
    expect(errors).toEqual([]);
    await page.goto("/videos");
    await expect(
      page.getByRole("button", { name: "Importer des vidéos", exact: true }),
    ).toBeEnabled();
    await page.reload();
    await expect(
      page.getByRole("button", { name: "Importer des vidéos", exact: true }),
    ).toBeEnabled();
    await page.getByRole("button", { name: "Paramètres", exact: true }).click();
    await expect(
      page.getByRole("link", { name: "Administration", exact: true }),
    ).toHaveCount(role === "admin" ? 1 : 0);
  });

  test(`${role} : l'analyse soumet une vraie requête avec CSRF et permet de préparer les recadrages`, async ({
    page,
  }) => {
    const { writes } = await fixture(page, role);
    await page.goto("/analyses");
    await page.getByLabel("Vidéo à analyser").selectOption(video.id);
    await expect(
      page.getByRole("button", { name: "Lancer l’analyse", exact: true }),
    ).toBeEnabled();
    // Le dossier de parcelle est facultatif pour une analyse simple.
    await page.getByLabel("Recevoir mon dossier biodiversité").uncheck();
    await page
      .getByRole("button", { name: "Lancer l’analyse", exact: true })
      .click();
    await expect
      .poll(
        () => writes.filter((write) => write.path.endsWith("/analyze")).length,
      )
      .toBe(1);
    expect(
      writes.find((write) => write.path.endsWith("/analyze"))?.body,
    ).toMatchObject({ detection_only: true, infer_every_n_frames: 10 });
    await expect(page).toHaveURL(/task=analysis-task/);
    await page
      .getByRole("button", { name: "Confirmer les espèces", exact: true })
      .click();
    await expect
      .poll(
        () =>
          writes.filter((write) => write.path.endsWith("/prepare-review"))
            .length,
      )
      .toBe(1);
    await page.screenshot({
      path: `test-results/analysis-${role}.png`,
      fullPage: true,
    });
  });

  test(`${role} : validation humaine et permissions documentaires`, async ({
    page,
  }) => {
    const { writes } = await fixture(page, role);
    await page.goto("/review");
    await page
      .getByRole("checkbox", {
        name: `Sélectionner ${video.filename}, image 1`,
        exact: true,
      })
      .check();
    await page.getByLabel("Espèce à attribuer").selectOption("chevreuil");
    await page
      .getByRole("button", { name: "Valider la sélection", exact: true })
      .click();
    await expect
      .poll(
        () =>
          writes.filter(
            (write) => write.path === "/review/samples/batch-decisions",
          ).length,
      )
      .toBe(1);
    await page.goto("/documents");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      "Documents scientifiques",
    );
    await expect(
      page.getByRole("button", { name: "Importer un document", exact: true }),
    ).toHaveCount(role === "admin" ? 1 : 0);
  });
}

test("un client ne peut pas entrer dans l'administration", async ({ page }) => {
  const { reads } = await fixture(page, "client");
  await page.goto("/admin/utilisateurs");
  await expect(page).toHaveURL(/\/$/);
  expect(reads).not.toContain("/admin/users");
});

test("les pages administrateur consultent les services et restent accessibles", async ({
  page,
}) => {
  const { reads } = await fixture(page, "admin");
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  for (const path of [
    "/admin",
    "/admin/utilisateurs",
    "/admin/videos",
    "/admin/analyses",
    "/admin/datasets",
    "/admin/training",
    "/admin/models",
    "/admin/evaluation",
    "/admin/documents",
  ]) {
    await page.goto(path);
    await expect(page.locator("h1")).toBeVisible();
    await expect(
      page.getByText(/Mode démonstration|Données fictives/),
    ).toHaveCount(0);
  }
  expect(errors).toEqual([]);
  expect(reads).toContain("/console/models");
  expect(reads).toContain("/admin/users");
});
