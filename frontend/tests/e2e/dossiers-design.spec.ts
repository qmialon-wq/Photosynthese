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
    await Promise.all(
      Array.from(
        document.querySelectorAll(".sym-photo,.sym-forest,.sf-project-photo"),
      ).map(
        (element) =>
          new Promise<void>((resolve, reject) => {
            const url = getComputedStyle(element).backgroundImage.match(
              /url\(["']?(.*?)["']?\)/,
            )?.[1];
            if (!url) return resolve();
            const image = new Image();
            image.onload = () => resolve();
            image.onerror = () =>
              reject(new Error(`Image indisponible : ${url}`));
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
async function activeAppearance(page: Page) {
  return page
    .locator('.sym-wheel-link[aria-current="page"]')
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
}
async function wheelState(page: Page) {
  return page.locator(".sym-wheel-link").evaluateAll((elements) =>
    elements.map((element) => {
      const style = getComputedStyle(element);
      const label = getComputedStyle(
        element.querySelector(".sym-wheel-label")!,
      );
      return {
        section: element.getAttribute("aria-label"),
        slot: element.getAttribute("data-slot"),
        left: style.left,
        top: style.top,
        width: style.width,
        height: style.height,
        color: style.color,
        background: style.backgroundImage,
        border: style.border,
        shadow: style.boxShadow,
        font: label.font,
        icon: Array.from(element.querySelectorAll("svg path")).map((path) =>
          path.getAttribute("d"),
        ),
      };
    }),
  );
}

test("trois captures en 1600 × 900 et non-régression du socle", async ({
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
  await page.screenshot({ path: testInfo.outputPath("accueil-1600x900.png") });
  const homeBefore = await page.screenshot({
    mask: [page.locator(".sym-wheel-link"), page.locator(".sym-demo-note")],
  });
  const homeWheel = await wheelState(page);
  const bounds = await page.locator(".sym-wheel-link.is-active").boundingBox();
  const appearance = await activeAppearance(page);
  const arc = await page.locator(".sym-wheel-arc path").getAttribute("d");
  const nav = page.getByRole("navigation", { name: "Navigation principale" });
  await nav.getByRole("link", { name: "Vidéothèque", exact: true }).click();
  await page.locator(".sv-video-card").first().waitFor();
  await ready(page);
  await expect(page.locator(".sv-pagination > p")).toContainText(
    "sur 248 vidéos",
  );
  await expect(
    page.locator(".sv-video-card").first().locator(".sv-status"),
  ).toHaveText("Validée");
  await page.screenshot({
    path: testInfo.outputPath("videotheque-1600x900.png"),
  });
  const videosBefore = await page.screenshot({
    mask: [page.locator(".sym-wheel-link"), page.locator(".sym-demo-note")],
  });
  const videosWheel = await wheelState(page);
  await nav.getByRole("link", { name: "Mes dossiers", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Mes dossiers", exact: true }),
  ).toBeVisible();
  await ready(page);
  await expect(page.locator(".sf-project-card")).toHaveCount(6);
  await expect(page.locator(".sf-page")).toBeInViewport({ ratio: 1 });
  expect(
    await nav
      .locator("a")
      .evaluateAll((elements) =>
        elements
          .sort(
            (a, b) =>
              Number(a.getAttribute("data-slot")) -
              Number(b.getAttribute("data-slot")),
          )
          .map((element) => element.getAttribute("aria-label")),
      ),
  ).toEqual([
    "Documents scientifiques",
    "Accueil",
    "Vidéothèque",
    "Mes dossiers",
    "Analyses",
    "Validation humaine",
  ]);
  await expect(nav.locator('[aria-current="page"]')).toHaveAttribute(
    "data-slot",
    "4",
  );
  expect(await nav.locator('[aria-current="page"]').boundingBox()).toEqual(
    bounds,
  );
  expect(await activeAppearance(page)).toEqual(appearance);
  expect(await page.locator(".sym-wheel-arc path").getAttribute("d")).toBe(arc);
  const cards = await page.locator(".sf-project-card").evaluateAll((elements) =>
    elements.map((element) => {
      const box = element.getBoundingClientRect();
      return { x: box.x, y: box.y };
    }),
  );
  expect(cards[0].y).toBe(cards[1].y);
  expect(cards[1].y).toBe(cards[2].y);
  expect(cards[3].y).toBeGreaterThan(cards[0].y);
  expect(cards[3].x).toBe(cards[0].x);
  await page.screenshot({
    path: testInfo.outputPath("mes-dossiers-1600x900.png"),
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
    path: testInfo.outputPath("accueil-retour-1600x900.png"),
  });
  expect(
    (
      await page.screenshot({
        mask: [page.locator(".sym-wheel-link"), page.locator(".sym-demo-note")],
      })
    ).equals(homeBefore),
  ).toBe(true);
  expect(await wheelState(page)).toEqual(homeWheel);
  await nav.getByRole("link", { name: "Vidéothèque", exact: true }).click();
  await page.locator(".sv-video-card").first().waitFor();
  await ready(page);
  expect(
    (
      await page.screenshot({
        mask: [page.locator(".sym-wheel-link"), page.locator(".sym-demo-note")],
      })
    ).equals(videosBefore),
  ).toBe(true);
  expect(await wheelState(page)).toEqual(videosWheel);
  expect(calls).toEqual([]);
});

test("recherche par nom, filtres combinés et pagination de douze dossiers", async ({
  page,
}) => {
  await page.goto("/parcelles");
  await expect(page.locator(".sf-page > .sv-pagination > p")).toHaveText(
    "1 – 6 sur 12 dossiers",
  );
  await page.getByRole("button", { name: "Page 2", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Bois du Ruisseau", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".sf-page > .sv-pagination > p")).toHaveText(
    "7 – 12 sur 12 dossiers",
  );
  await expect(
    page.getByRole("button", { name: "Suivant", exact: true }),
  ).toBeDisabled();
  await page
    .getByRole("searchbox", { name: "Rechercher un dossier", exact: true })
    .fill("FORET");
  await expect(page.locator(".sf-project-card")).toHaveCount(1);
  await expect(
    page.getByRole("heading", { name: "Forêt Est", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".sf-page > .sv-pagination > p")).toHaveText(
    "1 – 1 sur 1 dossier",
  );
  await page
    .getByRole("searchbox", { name: "Rechercher un dossier", exact: true })
    .fill("");
  await page
    .getByLabel("Filtrer par projet", { exact: true })
    .selectOption("forest");
  await expect(page.locator(".sf-project-card")).toHaveCount(4);
  await page
    .getByLabel("Filtrer par statut", { exact: true })
    .selectOption("pending");
  await expect(
    page.getByRole("heading", {
      name: "Aucun dossier ne correspond à votre recherche",
    }),
  ).toBeVisible();
  await expect(page.locator(".sf-page > .sv-pagination > p")).toHaveText(
    "0 – 0 sur 0 dossiers",
  );
  await page.getByRole("button", { name: "Réinitialiser les filtres" }).click();
  await expect(page.locator(".sf-project-card")).toHaveCount(6);
  await page
    .getByLabel("Filtrer par projet", { exact: true })
    .selectOption("wetland");
  await page
    .getByLabel("Filtrer par statut", { exact: true })
    .selectOption("validated");
  await expect(
    page.getByRole("heading", { name: "Zone Humide", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".sf-project-card")).toHaveCount(1);
  await page
    .getByRole("button", { name: "Actualiser les dossiers", exact: true })
    .click();
  await expect(page.locator(".sf-project-card")).toHaveCount(6);
});

test("ouverture du dossier et menus au clavier sans traitement réel", async ({
  page,
}) => {
  await page.goto("/parcelles");
  const opener = page.getByRole("button", {
    name: "Ouvrir le dossier Parcelle Nord",
    exact: true,
  });
  await opener.click();
  const dialog = page.getByRole("dialog", {
    name: "Parcelle Nord",
    exact: true,
  });
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText("données fictives");
  await expect(dialog).toContainText("42 vidéos");
  await expect(dialog).toContainText("3 espèces");
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
  await expect(opener).toBeFocused();
  await page
    .getByRole("button", { name: "Actions pour Haie Ouest", exact: true })
    .click();
  await expect(
    page.getByRole("menuitem", { name: "Ouvrir le dossier", exact: true }),
  ).toBeFocused();
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("dialog", { name: "Haie Ouest", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Fermer la fenêtre" }).click();
  await page
    .getByRole("button", { name: "Actions pour Haie Ouest", exact: true })
    .click();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("menu")).toHaveCount(0);
  await page
    .getByRole("button", { name: "Actions pour Haie Ouest", exact: true })
    .click();
  await page
    .getByRole("heading", { name: "Mes dossiers", exact: true })
    .click();
  await expect(page.getByRole("menu")).toHaveCount(0);
});

test("action principale reliée à la Vidéothèque existante", async ({
  page,
}) => {
  const calls: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/api/")) calls.push(request.url());
  });
  await page.goto("/parcelles");
  await page
    .getByRole("link", { name: "Choisir ou importer des vidéos", exact: true })
    .click();
  await expect(page).toHaveURL(/\/videos$/);
  await expect(page.locator(".sv-video-card")).toHaveCount(4);
  expect(calls).toEqual([]);
});

test("adaptation mobile et mouvements réduits", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/parcelles");
  await ready(page);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await expect(page.locator(".sf-project-card")).toHaveCount(6);
  await page
    .getByRole("button", {
      name: "Ouvrir le dossier Parcelle Nord",
      exact: true,
    })
    .hover();
  expect(
    await page
      .locator(".sf-project-card")
      .first()
      .evaluate((element) => getComputedStyle(element).transform),
  ).toBe("none");
  await page.mouse.move(0, 0);
  await page.screenshot({
    path: testInfo.outputPath("mes-dossiers-mobile.png"),
    fullPage: true,
  });
});
