import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
test.use({ viewport: { width: 1600, height: 900 } });
async function ready(page: Page) {
  await page.mouse.move(0, 0);
  await page.evaluate(async () => {
    await document.fonts.ready;
    await Promise.all(
      [...document.images].map((image) => image.decode().catch(() => {})),
    );
    const backgrounds = Array.from(
      document.querySelectorAll(".sv-thumbnail,.sym-forest"),
    );
    await Promise.all(
      backgrounds.map(
        (element) =>
          new Promise<void>((resolve) => {
            const url = getComputedStyle(element).backgroundImage.match(
              /url\(["']?(.*?)["']?\)/,
            )?.[1];
            if (!url) return resolve();
            const image = new Image();
            image.onload = () => resolve();
            image.onerror = () => resolve();
            image.src = url;
          }),
      ),
    );
    await new Promise<void>((resolve) =>
      requestAnimationFrame(() => resolve()),
    );
    await Promise.all(
      document
        .getAnimations()
        .map((animation) => animation.finished.catch(() => {})),
    );
  });
}

test("captures jumelées Accueil et Vidéothèque, roue et absence de régression", async ({
  page,
}, testInfo) => {
  const calls: string[] = [];
  page.on("request", (request) => {
    if (new URL(request.url()).pathname.startsWith("/api"))
      calls.push(request.url());
  });
  await page.goto("/");
  await page.locator(".sym-home").waitFor();
  await ready(page);
  await page.screenshot({
    path: testInfo.outputPath("accueil-1600x900.png"),
  });
  // Le filtre de verre du bouton mobile est recomposé par Chromium après l’animation.
  // Sa géométrie et son apparence CSS sont vérifiées séparément ci-dessous.
  const beforeStable = await page.screenshot({
    mask: [page.locator(".sym-wheel-link.is-active")],
  });
  const nav = page.getByRole("navigation", { name: "Navigation principale" });
  const homeBounds = await nav.locator('[aria-current="page"]').boundingBox();
  const arc = await page.locator(".sym-wheel-arc path").getAttribute("d");
  const appearance = await nav
    .locator('[aria-current="page"]')
    .evaluate((element) => {
      const style = getComputedStyle(element);
      return [
        style.backgroundImage,
        style.borderColor,
        style.borderRadius,
        style.boxShadow,
        style.color,
      ];
    });
  await nav.getByRole("link", { name: "Vidéothèque", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Vidéothèque", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".sv-video-card")).toHaveCount(4);
  await ready(page);
  const ordered = await nav
    .locator("a")
    .evaluateAll((elements) =>
      elements
        .sort(
          (a, b) =>
            Number(a.getAttribute("data-slot")) -
            Number(b.getAttribute("data-slot")),
        )
        .map((element) => element.getAttribute("aria-label")),
    );
  expect(ordered).toEqual([
    "Validation humaine",
    "Documents scientifiques",
    "Accueil",
    "Vidéothèque",
    "Mes dossiers",
    "Analyses",
  ]);
  expect(await nav.locator('[aria-current="page"]').boundingBox()).toEqual(
    homeBounds,
  );
  expect(
    await nav.locator('[aria-current="page"]').evaluate((element) => {
      const style = getComputedStyle(element);
      return [
        style.backgroundImage,
        style.borderColor,
        style.borderRadius,
        style.boxShadow,
        style.color,
      ];
    }),
  ).toEqual(appearance);
  expect(await page.locator(".sym-wheel-arc path").getAttribute("d")).toBe(arc);
  await expect(page.locator(".sv-page")).toBeInViewport({ ratio: 1 });
  await page.screenshot({
    path: testInfo.outputPath("videotheque-1600x900.png"),
  });
  const scan = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(
    scan.violations.map((item) => ({
      id: item.id,
      nodes: item.nodes.map((node) => ({
        target: node.target,
        summary: node.failureSummary,
      })),
    })),
  ).toEqual([]);
  await nav.getByRole("link", { name: "Accueil", exact: true }).click();
  await page.locator(".sym-home").waitFor();
  await ready(page);
  await page.screenshot({
    path: testInfo.outputPath("accueil-apres-videotheque-1600x900.png"),
  });
  const afterStable = await page.screenshot({
    mask: [page.locator(".sym-wheel-link.is-active")],
  });
  expect(afterStable.equals(beforeStable)).toBe(true);
  expect(await nav.locator('[aria-current="page"]').boundingBox()).toEqual(
    homeBounds,
  );
  expect(
    await nav.locator('[aria-current="page"]').evaluate((element) => {
      const style = getComputedStyle(element);
      return [
        style.backgroundImage,
        style.borderColor,
        style.borderRadius,
        style.boxShadow,
        style.color,
      ];
    }),
  ).toEqual(appearance);
  expect(calls).toEqual([]);
});

test("sélection entre pages, compteur et préparation de démonstration", async ({
  page,
}) => {
  await page.goto("/videos");
  const prepare = page.getByRole("button", { name: /Préparer un dossier/ });
  await expect(prepare).toBeDisabled();
  await page
    .getByRole("checkbox", { name: "Sélectionner VID_00124.mp4", exact: true })
    .check();
  await page
    .getByRole("checkbox", { name: "Sélectionner VID_00125.mp4", exact: true })
    .check();
  await expect(prepare).toContainText("2 vidéos");
  expect(
    await page
      .getByRole("checkbox", { name: "Sélectionner les vidéos de cette page" })
      .evaluate((input: HTMLInputElement) => input.indeterminate),
  ).toBe(true);
  await page.getByRole("button", { name: "Suivant", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "VID_00128.mp4" }),
  ).toBeVisible();
  await page
    .getByRole("checkbox", { name: "Sélectionner les vidéos de cette page" })
    .check();
  await expect(prepare).toContainText("6 vidéos");
  await page.getByRole("button", { name: "Précédent", exact: true }).click();
  await expect(
    page.getByRole("checkbox", {
      name: "Sélectionner VID_00124.mp4",
      exact: true,
    }),
  ).toBeChecked();
  await expect(
    page.getByRole("checkbox", {
      name: "Sélectionner VID_00126.mp4",
      exact: true,
    }),
  ).not.toBeChecked();
  await page
    .getByRole("button", { name: "Effacer la sélection", exact: true })
    .click();
  await expect(prepare).toBeDisabled();
  await page
    .getByRole("checkbox", { name: "Sélectionner les vidéos de cette page" })
    .check();
  await prepare.click();
  const dialog = page.getByRole("dialog", {
    name: "Préparer un dossier",
    exact: true,
  });
  await expect(dialog).toBeVisible();
  await expect(dialog.locator("li")).toHaveCount(4);
  await expect(dialog).toContainText("aucun dossier réel");
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
});

test("recherche, filtres combinés, résultat vide et 62 pages", async ({
  page,
}) => {
  await page.goto("/videos");
  await page
    .getByRole("searchbox", { name: "Rechercher une vidéo" })
    .fill("VID_00124");
  await expect(page.locator(".sv-video-card")).toHaveCount(1);
  await page
    .getByLabel("Filtrer par espèce", { exact: true })
    .selectOption("Renard");
  await expect(
    page.getByRole("heading", {
      name: "Aucune vidéo ne correspond à votre recherche",
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Réinitialiser les filtres" }).click();
  await expect(page.locator(".sv-video-card")).toHaveCount(4);
  await page
    .getByLabel("Filtrer par espèce", { exact: true })
    .selectOption("Renard");
  await page
    .getByLabel("Filtrer par statut", { exact: true })
    .selectOption("pending");
  await expect(page.locator(".sv-pagination > p")).toContainText(
    "sur 62 vidéos",
  );
  await page.getByRole("button", { name: "Page 2", exact: true }).click();
  await page
    .getByLabel("Filtrer par statut", { exact: true })
    .selectOption("validated");
  await expect(
    page.getByRole("heading", {
      name: "Aucune vidéo ne correspond à votre recherche",
    }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Actualiser les vidéos", exact: true })
    .click();
  await page.getByRole("button", { name: "Page 62", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "VID_00371.mp4" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Suivant", exact: true }),
  ).toBeDisabled();
  await expect(page.locator(".sv-pagination > p")).toContainText(
    "245 – 248 sur 248",
  );
});

test("menus au clavier, aperçu et import clairement simulés sans API", async ({
  page,
}) => {
  const calls: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/api/")) calls.push(request.url());
  });
  await page.goto("/videos");
  await page
    .getByRole("button", { name: "Actions pour VID_00124.mp4", exact: true })
    .click();
  await expect(
    page.getByRole("menuitem", { name: "Prévisualiser", exact: true }),
  ).toBeFocused();
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("Enter");
  const details = page.getByRole("dialog", {
    name: "Informations de la vidéo",
  });
  await expect(details).toBeVisible();
  await expect(details).toContainText("fictives");
  await page.getByRole("button", { name: "Fermer la fenêtre" }).click();
  await page
    .getByRole("button", { name: "Prévisualiser VID_00125.mp4", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toContainText(
    "lecture vidéo réelle n’est pas activée",
  );
  await page.keyboard.press("Escape");
  await page
    .getByRole("button", { name: "Importer des vidéos", exact: true })
    .click();
  const importer = page.getByRole("dialog", {
    name: "Importer des vidéos",
    exact: true,
  });
  await expect(importer).toContainText("aucun fichier n’est envoyé");
  await importer.locator('input[type="file"]').setInputFiles({
    name: "demo.mp4",
    mimeType: "video/mp4",
    buffer: Buffer.from("Fichier fictif de test, sans video"),
  });
  await importer
    .getByRole("button", { name: "Confirmer la simulation" })
    .click();
  await expect(page.locator(".sv-feedback")).toContainText(
    "Aucun fichier n’a été envoyé",
  );
  await expect(page.locator(".sv-stats")).toContainText("248");
  expect(calls).toEqual([]);
});

test("Vidéothèque utilisable sur mobile", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/videos");
  await ready(page);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await expect(page.locator(".sv-video-card")).toHaveCount(4);
  await page
    .getByRole("checkbox", { name: "Sélectionner VID_00124.mp4", exact: true })
    .check();
  await expect(
    page.getByRole("button", { name: /Préparer un dossier/ }),
  ).toContainText("1 vidéo");
  await page.screenshot({
    path: testInfo.outputPath("videotheque-mobile.png"),
    fullPage: true,
  });
});
