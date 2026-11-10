import {
  openDisplaySettings,
  closeDisplaySettings,
  selectSource,
  expectSource,
} from "./display-settings";
import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
const sections = [
  [
    "/admin/utilisateurs",
    "Utilisateurs",
    "Gestion des utilisateurs",
    "01-utilisateurs",
  ],
  [
    "/admin",
    "Vue d’ensemble",
    "La biodiversité, en perspective.",
    "02-vue-ensemble",
  ],
  ["/admin/videos", "Gestion des vidéos", "Vidéothèque", "03-videos"],
  ["/admin/analyses", "Réglages d’analyse", "Analyse vidéo", "04-analyses"],
  ["/admin/datasets", "Datasets", "Datasets", "05-datasets"],
  ["/admin/training", "Entraînements", "Entraînements", "06-entrainements"],
  ["/admin/models", "Modèles", "Modèles", "07-modeles"],
  ["/admin/evaluation", "Évaluation", "Évaluation", "08-evaluation"],
  [
    "/admin/documents",
    "Documents scientifiques",
    "Documents scientifiques",
    "09-documents",
  ],
] as const;
const session = (role: "admin" | "client") => ({
  user: {
    id: "test-session",
    display_name: "Session de validation",
    email: "validation@example.test",
    role,
    created_at: "2026-11-01",
    deleted_at: null,
  },
  csrf_token: "test-csrf",
});
async function authenticate(
  page: Page,
  role: "admin" | "client" | null = "admin",
) {
  await page.route("**/api/auth/me", (route) =>
    route.fulfill({
      status: role ? 200 : 401,
      json: role ? session(role) : { detail: "Session requise" },
    }),
  );
  await page.route("**/api/auth/status", (route) =>
    route.fulfill({ json: { initialized: true, registration_enabled: false } }),
  );
}
async function ready(page: Page) {
  await page.evaluate(async () => {
    await document.fonts.ready;
    await Promise.all(
      [...document.images].map((i) => i.decode().catch(() => {})),
    );
  });
}
test.use({ viewport: { width: 1600, height: 900 } });
for (const [path, label, heading, file] of sections) {
  test(`administration : ${label}, rendu et accessibilité`, async ({
    page,
  }) => {
    await authenticate(page);
    const errors: string[] = [],
      business: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    page.on("request", (r) => {
      const p = new URL(r.url()).pathname;
      if (p.startsWith("/api/") && !p.startsWith("/api/auth/"))
        business.push(p);
    });
    await page.goto(path);
    await expect(page.locator("h1")).toHaveText(heading);
    const nav = page.getByRole("navigation", {
      name: "Navigation administrative",
    });
    await expect(nav.getByRole("link")).toHaveCount(11);
    await expect(
      nav.getByRole("link", { name: label, exact: true }),
    ).toHaveAttribute("aria-current", "page");
    await expect(page.locator(".sym-wheel")).toHaveCount(0);
    await expectSource(page, "demo");
    if (path === "/admin/documents")
      await page
        .getByLabel("Espèce", { exact: true })
        .selectOption("chevreuil");
    await ready(page);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    const result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(
      result.violations.map((v) => ({
        id: v.id,
        nodes: v.nodes.map((n) => ({
          target: n.target,
          summary: n.failureSummary,
        })),
      })),
    ).toEqual([]);
    await page.screenshot({
      path: `../output/symbiose/etape-9/${file}-1600x900.png`,
    });
    expect(errors).toEqual([]);
    expect(business).toEqual([]);
  });
}
test("engrenage, navigation SPA et retour à la dernière rubrique avec la roue intacte", async ({
  page,
}) => {
  await authenticate(page);
  await page.goto("/parcelles");
  const arc = await page.locator(".sym-wheel-arc path").getAttribute("d");
  await page.evaluate(() => {
    document.body.dataset.spa = "conserve";
  });
  await page.getByRole("button", { name: "Paramètres", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Paramètres d’affichage" }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Administration", exact: true })
    .waitFor();
  await page.screenshot({
    path: "../output/symbiose/etape-9/menu-engrenage-1600x900.png",
  });
  await page.getByRole("link", { name: "Administration", exact: true }).click();
  await expect(page).toHaveURL(/\/admin$/);
  for (const [path, label] of sections) {
    await page
      .getByRole("navigation", { name: "Navigation administrative" })
      .getByRole("link", { name: label, exact: true })
      .click();
    await expect(page).toHaveURL(new RegExp(`${path}$`));
  }
  await page
    .getByRole("link", { name: "Retour à l’espace observation" })
    .click();
  await expect(page).toHaveURL(/\/parcelles$/);
  expect(await page.locator(".sym-wheel-arc path").getAttribute("d")).toBe(arc);
  await expect(
    page
      .getByRole("navigation", { name: "Navigation principale" })
      .getByRole("link"),
  ).toHaveCount(6);
  await expectSource(page, "demo");
  expect(await page.locator("body").getAttribute("data-spa")).toBe("conserve");
});
for (const role of ["client", null] as const)
  test(`accès protégé : ${role || "anonyme"}, même avec un faux rôle stocké`, async ({
    page,
  }) => {
    await authenticate(page, role);
    await page.addInitScript(() => localStorage.setItem("role", "admin"));
    await page.goto("/");
    await page.getByRole("button", { name: "Paramètres", exact: true }).click();
    await expect(
      page.getByRole("link", { name: "Administration", exact: true }),
    ).toHaveCount(0);
    for (const [path] of sections) {
      await page.goto(path);
      await expect(page).toHaveURL(role ? /\/$/ : /\/connexion$/);
      await expect(page.locator(".adm-shell")).toHaveCount(0);
    }
  });
test("comptes fictifs : création puis suppression locale sans requête métier", async ({
  page,
}) => {
  await authenticate(page);
  const writes: string[] = [];
  page.on("request", (r) => {
    if (r.url().includes("/api/") && !["GET", "HEAD"].includes(r.method()))
      writes.push(r.url());
  });
  await page.goto("/admin/utilisateurs");
  await page.getByLabel("Nom du profil").fill("Test de suppression locale");
  await page
    .getByLabel("Adresse e-mail", { exact: true })
    .fill("local@example.test");
  await page.getByLabel("Mot de passe initial").fill("simulation-locale-2026");
  await page
    .getByRole("button", { name: "Créer le compte", exact: true })
    .click();
  const row = page.getByRole("row").filter({ hasText: "local@example.test" });
  await expect(row).toHaveCount(1);
  await row.getByRole("button", { name: "Supprimer le compte" }).click();
  await page.getByLabel("Saisir SUPPRIMER").fill("SUPPRIMER");
  await page.getByRole("button", { name: "Confirmer la suppression" }).click();
  await expect(row).toHaveCount(0);
  expect(writes).toEqual([]);
});
test("progression simulée et changement de mode : aucun identifiant fictif envoyé au backend", async ({
  page,
}) => {
  await authenticate(page);
  const calls: string[] = [];
  await page.route("**/api/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    calls.push(path);
    return route.fulfill({ json: [] });
  });
  await authenticate(page);
  await page.goto("/admin/training");
  await page
    .getByLabel("Dataset d’entraînement")
    .selectOption("demo-dataset-1");
  await page.getByRole("button", { name: "Démarrer l’entraînement" }).click();
  await expect(page).toHaveURL(/task=demo-/);
  await expect(
    page.getByText("Progression simulée · aucun worker réel"),
  ).toBeVisible({ timeout: 8000 });
  await selectSource(page, "real");
  await expect(page).toHaveURL(/\/admin\/training$/);
  await expect(
    page.getByLabel("Dataset d’entraînement").locator("option"),
  ).toHaveCount(1);
  expect(calls.some((path) => path.includes("demo-"))).toBe(false);
  await page
    .getByRole("navigation", { name: "Navigation administrative" })
    .getByRole("link", { name: "Modèles", exact: true })
    .click();
  await expect(page.getByText("Aucun modèle enregistré")).toBeVisible();
  await page
    .getByRole("link", { name: "Retour à l’espace observation" })
    .click();
  await expectSource(page, "real");
});
test("action réelle : annulation sans envoi, puis confirmation et CSRF sur le service existant", async ({
  page,
}) => {
  let writes = 0;
  await page.route("**/api/**", (route) => {
    const req = route.request(),
      path = new URL(req.url()).pathname;
    if (path === "/api/console/training" && req.method() === "POST") {
      writes++;
      expect(req.headers()["x-csrf-token"]).toBe("test-csrf");
      return route.fulfill({ json: { id: "real-task", status: "queued" } });
    }
    if (path === "/api/console/training/datasets")
      return route.fulfill({
        json: [
          {
            id: "server-dataset",
            name: "Dataset serveur",
            source: "review",
            ready: true,
          },
        ],
      });
    return route.fulfill({ json: [] });
  });
  await authenticate(page);
  await page.goto("/admin/training");
  await selectSource(page, "real");
  await page
    .getByLabel("Dataset d’entraînement")
    .selectOption("server-dataset");
  await page.getByRole("button", { name: "Démarrer l’entraînement" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  expect(writes).toBe(0);
  await page.screenshot({
    path: "../output/symbiose/etape-9/confirmation-reelle-1600x900.png",
  });
  await dialog.getByRole("button", { name: "Annuler", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  expect(writes).toBe(0);
  await page.getByRole("button", { name: "Démarrer l’entraînement" }).click();
  await dialog
    .getByRole("button", { name: "Confirmer l’action réelle" })
    .click();
  await expect(page).toHaveURL(/task=real-task/);
  expect(writes).toBe(1);
});
test("erreur du service réel : aucun modèle ni métrique fictifs en remplacement", async ({
  page,
}) => {
  await page.route("**/api/**", (route) =>
    route.fulfill({ status: 503, json: { detail: "Service non disponible" } }),
  );
  await authenticate(page);
  await page.goto("/admin/models");
  await selectSource(page, "real");
  await expect(page.getByRole("alert")).toContainText("Service non disponible");
  await expect(page.locator(".model-card")).toHaveCount(0);
  await ready(page);
  await page.screenshot({
    path: "../output/symbiose/etape-9/service-indisponible-1600x900.png",
  });
});
for (const width of [1280, 390])
  test(`navigation et formulaires à ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await authenticate(page);
    await page.goto("/admin/training");
    if (width === 390) {
      await page
        .getByRole("button", { name: "Navigation administrative", exact: true })
        .click();
      await expect(
        page.getByRole("link", { name: "Utilisateurs", exact: true }),
      ).toBeFocused();
      await page.keyboard.press("Escape");
      await expect(
        page.getByRole("button", {
          name: "Navigation administrative",
          exact: true,
        }),
      ).toBeFocused();
    }
    await expect(page.getByLabel("Dataset d’entraînement")).toBeInViewport();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    expect(
      await page
        .locator(".adm-content")
        .evaluate((e) => e.scrollWidth <= e.clientWidth),
    ).toBe(true);
    await ready(page);
    await page.screenshot({
      path: `../output/symbiose/etape-9/entrainements-${width}x900.png`,
    });
  });

test("VideoCard partagé : sélection, filtre et aperçu fixe explicitement simulé", async ({
  page,
}) => {
  await authenticate(page);
  await page.goto("/admin/videos");
  await page
    .getByRole("button", { name: "Prévisualiser VID_00124.mp4", exact: true })
    .click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toContainText("Aperçu fixe");
  await expect(dialog.locator("video")).toHaveCount(0);
  await page.keyboard.press("Escape");
  await page.getByLabel("Sélectionner VID_00124.mp4", { exact: true }).check();
  await expect(
    page.getByRole("button", {
      name: "Préparer un dossier (1 vidéo)",
      exact: true,
    }),
  ).toBeEnabled();
  await page.getByPlaceholder("Rechercher une vidéo…").fill("VID_00125");
  await expect(page.locator(".sv-video-wrapper")).toHaveCount(1);
  await page
    .getByRole("button", { name: "Prévisualiser VID_00125.mp4", exact: true })
    .click();
  await page
    .getByRole("link", { name: "Configurer l’analyse", exact: true })
    .click();
  await expect(page).toHaveURL(/admin\/analyses\?video=demo-video-125$/);
  await expect(
    page.getByRole("heading", { name: "Configurer l’analyse", exact: true }),
  ).toBeVisible();
});
test("corpus commun : lecture, retrait local et résultat conservé dans l’espace observation", async ({
  page,
}) => {
  await authenticate(page);
  await page.goto("/admin/documents");
  await page.getByLabel("Espèce", { exact: true }).selectOption("chevreuil");
  await expect(page.locator(".sd-document-card")).toHaveCount(5);
  await page
    .locator(".sd-document-card")
    .first()
    .getByRole("button", { name: /Lire le document/ })
    .click();
  await expect(page.getByRole("dialog")).toContainText("EXEMPLE FICTIF");
  await page.keyboard.press("Escape");
  await page.getByLabel("Tout sélectionner sur cette page").check();
  await page
    .getByRole("button", { name: "Retirer du corpus", exact: true })
    .click();
  await expect(page.locator(".sd-document-card")).toHaveCount(0);
  await page
    .getByRole("link", { name: "Retour à l’espace observation" })
    .click();
  await page
    .getByRole("navigation", { name: "Navigation principale" })
    .getByRole("link", { name: "Documents scientifiques" })
    .click();
  await page
    .getByLabel("Espèce du corpus", { exact: true })
    .selectOption("chevreuil");
  await expect(page.locator(".sd-document-card")).toHaveCount(0);
});
test("dataset local : version consultable après progression et absence de fausse archive", async ({
  page,
}) => {
  await authenticate(page);
  await page.goto("/admin/datasets");
  await page
    .getByLabel("Nom de la version", { exact: true })
    .fill("Version locale de validation");
  await page.getByRole("button", { name: "Construire le dataset" }).click();
  await expect(page.locator(".version-list")).toContainText(
    "Version locale de validation",
    { timeout: 10000 },
  );
  await page
    .locator(".version-list")
    .getByRole("button")
    .filter({ hasText: "Version locale de validation" })
    .click();
  await expect(page.getByRole("table")).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Télécharger le ZIP" }),
  ).toHaveCount(0);
});
test("registre local : enregistrement distinct de l’activation et résultats d’évaluation", async ({
  page,
}) => {
  await authenticate(page);
  await page.goto("/admin/models");
  await page
    .getByLabel("Nom du modèle", { exact: true })
    .fill("Checkpoint fictif supplémentaire");
  await page
    .getByLabel("Chemin relatif à data/checkpoints", { exact: true })
    .fill("exemple/best.pt");
  await page.getByRole("button", { name: "Vérifier et enregistrer" }).click();
  const candidate = page
    .locator(".model-card")
    .filter({ hasText: "Checkpoint fictif supplémentaire" });
  await expect(candidate).toHaveCount(1, { timeout: 10000 });
  await expect(
    candidate.getByText("Modèle actif", { exact: true }),
  ).toHaveCount(0);
  await candidate.getByRole("button", { name: "Définir comme actif" }).click();
  await expect(page.getByText("Modèle actif", { exact: true })).toHaveCount(1);
  await expect(
    candidate.getByText("Modèle actif", { exact: true }),
  ).toBeVisible();
  await candidate.getByRole("link", { name: "Métriques" }).click();
  await page.getByLabel("Dataset à évaluer").selectOption("demo-dataset-1");
  await page.getByRole("button", { name: "Lancer l’évaluation" }).click();
  await expect(
    page.getByRole("region", { name: "Suivi de tâche" }),
  ).toContainText("Simulation locale terminée", { timeout: 10000 });
  await expect(page.locator(".confusion")).toBeVisible();
  const scan = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(scan.violations).toEqual([]);
  await page.locator(".metrics-panel").scrollIntoViewIfNeeded();
  // Laisser le compositeur repeindre les surfaces en verre après le défilement.
  await page.evaluate(async () => {
    await new Promise<void>((resolve) =>
      requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
    );
  });
  await page.screenshot({
    animations: "disabled",
    path: "../output/symbiose/etape-9/evaluation-resultats-1600x900.png",
  });
});
