import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test.use({ viewport: { width: 1600, height: 900 } });
async function ready(page: Page) {
  await page.mouse.move(0, 0);
  await page.evaluate(async () => {
    await document.fonts.ready;
    await Promise.all(
      Array.from(document.images).map((image) =>
        image.decode().catch(() => {}),
      ),
    );
    await Promise.all(
      Array.from(
        document.querySelectorAll(
          ".sym-photo,.sym-forest,.sf-project-photo,.sa-poster,.sr-observation-photo",
        ),
      ).map(
        (element) =>
          new Promise<void>((resolve, reject) => {
            const url = getComputedStyle(element).backgroundImage.match(
              /url\(["']?(.*?)["']?\)/,
            )?.[1];
            if (!url) return resolve();
            const image = new Image();
            image.onload = () => resolve();
            image.onerror = () => reject(new Error(url));
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
  await expect
    .poll(() =>
      page
        .locator(".sr-observation-preview video")
        .evaluateAll((videos) =>
          videos.every(
            (video) =>
              (video as HTMLVideoElement).readyState >= 2 &&
              !(video as HTMLVideoElement).seeking,
          ),
        ),
    )
    .toBe(true);
}
async function wheel(page: Page) {
  return page.locator(".sym-wheel-link").evaluateAll((elements) =>
    elements.map((element) => {
      const s = getComputedStyle(element),
        r = element.getBoundingClientRect();
      return {
        section: element.getAttribute("aria-label"),
        slot: element.getAttribute("data-slot"),
        x: r.x,
        y: r.y,
        width: r.width,
        height: r.height,
        color: s.color,
        background: s.backgroundImage,
        border: s.border,
        radius: s.borderRadius,
        shadow: s.boxShadow,
        font: getComputedStyle(element.querySelector(".sym-wheel-label")!).font,
        icon: Array.from(element.querySelectorAll("svg path")).map((path) =>
          path.getAttribute("d"),
        ),
      };
    }),
  );
}
async function open(page: Page) {
  await page.goto("/review");
  await page.locator(".sr-observation").first().waitFor();
  await ready(page);
}
const card = (page: Page, number: number) =>
  page.locator(`[data-observation-id="observation-${number}"]`);
const selectionCount = (page: Page) => page.locator(".sr-selection-count");
const allCheckbox = (page: Page) =>
  page.getByRole("checkbox", { name: "Sélectionner la page", exact: true });

test("cinq captures, grille 4 × 2, roue fixe et quatre pages sans régression", async ({
  page,
}, info) => {
  test.setTimeout(120000);
  const calls: string[] = [],
    errors: string[] = [];
  page.on("request", (request) => {
    if (new URL(request.url()).pathname.startsWith("/api"))
      calls.push(request.url());
  });
  page.on("pageerror", (error) => errors.push(error.message));
  const snapshots = new Map<
    string,
    { image: Buffer; wheel: Awaited<ReturnType<typeof wheel>> }
  >();
  const routes = [
    { path: "/", name: "accueil", selector: ".sym-home" },
    { path: "/videos", name: "videotheque", selector: ".sv-video-card" },
    { path: "/parcelles", name: "mes-dossiers", selector: ".sf-project-card" },
    { path: "/analyses", name: "analyse-video", selector: ".sa-player" },
  ];
  for (const route of routes) {
    await page.goto(route.path);
    await page.locator(route.selector).first().waitFor();
    await ready(page);
    await page.screenshot({
      path: info.outputPath(`${route.name}-1600x900.png`),
    });
    snapshots.set(route.path, {
      image: await page.screenshot({
        mask: [page.locator(".sym-wheel-link"), page.locator(".sym-demo-note")],
      }),
      wheel: await wheel(page),
    });
  }
  const arc = await page.locator(".sym-wheel-arc path").getAttribute("d");
  await page.locator('.sym-wheel-link[data-section="/review"]').click();
  await page.locator(".sr-page").waitFor();
  await ready(page);
  const state = await wheel(page),
    active = state.find((item) => item.slot === "4")!;
  expect(
    state
      .slice()
      .sort((a, b) => Number(a.slot) - Number(b.slot))
      .map((item) => item.section),
  ).toEqual([
    "Vidéothèque",
    "Mes dossiers",
    "Analyses",
    "Validation humaine",
    "Documents scientifiques",
    "Accueil",
  ]);
  const homeActive = snapshots
    .get("/")!
    .wheel.find((item) => item.slot === "4")!;
  expect({ ...active, section: "", font: "", icon: [] }).toEqual({
    ...homeActive,
    section: "",
    font: "",
    icon: [],
  });
  expect(active.width).toBe(186);
  expect(active.height).toBe(62);
  expect(await page.locator(".sym-wheel-arc path").getAttribute("d")).toBe(arc);
  await expect(page.locator(".sr-observation")).toHaveCount(8);
  await expect(page.locator(".sr-page")).toBeInViewport({ ratio: 1 });
  const positions = await page
    .locator(".sr-observation")
    .evaluateAll((elements) =>
      elements.map((element) => {
        const r = element.getBoundingClientRect();
        return { x: r.x, y: r.y };
      }),
    );
  expect(new Set(positions.map((p) => p.y)).size).toBe(2);
  expect(new Set(positions.map((p) => p.x)).size).toBe(4);
  expect(positions[0].x).toBe(positions[4].x);
  expect(positions[4].y).toBeGreaterThan(positions[0].y);
  const scan = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(
    scan.violations.map((v) => ({
      id: v.id,
      nodes: v.nodes.map((n) => ({
        target: n.target,
        summary: n.failureSummary,
      })),
    })),
  ).toEqual([]);
  await page.screenshot({
    path: info.outputPath("validation-humaine-1600x900.png"),
  });
  for (const route of routes) {
    await page.locator(`.sym-wheel-link[data-section="${route.path}"]`).click();
    await page.locator(route.selector).first().waitFor();
    await ready(page);
    expect(await wheel(page)).toEqual(snapshots.get(route.path)!.wheel);
    expect(
      (
        await page.screenshot({
          mask: [
            page.locator(".sym-wheel-link"),
            page.locator(".sym-demo-note"),
          ],
        })
      ).equals(snapshots.get(route.path)!.image),
    ).toBe(true);
  }
  expect(calls).toEqual([]);
  expect(errors).toEqual([]);
});

test("sélection locale, état partiel et protection des images de test", async ({
  page,
}) => {
  await open(page);
  await expect(selectionCount(page)).toHaveText("0 sélectionnée");
  await expect(
    page.getByRole("button", { name: "Valider la sélection", exact: true }),
  ).toBeDisabled();
  await card(page, 1).getByRole("checkbox").check();
  await expect(selectionCount(page)).toHaveText("1 sélectionnée");
  await expect(card(page, 1)).toHaveClass(/is-selected/);
  expect(
    await allCheckbox(page).evaluate(
      (input) => (input as HTMLInputElement).indeterminate,
    ),
  ).toBe(true);
  await card(page, 1).getByRole("checkbox").uncheck();
  await allCheckbox(page).check();
  await expect(selectionCount(page)).toHaveText("6 sélectionnées");
  await expect(page.locator(".sr-observation.is-selected")).toHaveCount(6);
  for (const number of [6, 7]) {
    await expect(card(page, number).getByRole("checkbox")).toBeDisabled();
    await expect(card(page, number)).not.toHaveClass(/is-selected/);
  }
  await page
    .getByRole("button", { name: "Désélectionner", exact: true })
    .click();
  await expect(selectionCount(page)).toHaveText("0 sélectionnée");
  await expect(allCheckbox(page)).not.toBeChecked();
});

test("filtres combinés, résultat vide et sélection limitée aux observations affichées", async ({
  page,
}) => {
  await open(page);
  await allCheckbox(page).check();
  await page
    .getByLabel("Filtrer les observations par qualité", { exact: true })
    .selectOption("blurry");
  await expect(selectionCount(page)).toHaveText("0 sélectionnée");
  await expect(page.locator(".sr-observation")).toHaveCount(3);
  await allCheckbox(page).check();
  await expect(selectionCount(page)).toHaveText("2 sélectionnées");
  await page
    .getByLabel("Filtrer les observations par espèce", { exact: true })
    .selectOption("ecureuil");
  await expect(page.locator(".sr-observation")).toHaveCount(0);
  await expect(
    page.getByRole("heading", {
      name: "Aucune observation à afficher",
      exact: true,
    }),
  ).toBeVisible();
  await expect(allCheckbox(page)).toBeDisabled();
  await page
    .getByRole("button", { name: "Réinitialiser les filtres", exact: true })
    .click();
  await expect(page.locator(".sr-observation")).toHaveCount(8);
  await expect(selectionCount(page)).toHaveText("0 sélectionnée");
  await page
    .getByLabel("Filtrer les observations par espèce", { exact: true })
    .selectOption("chevreuil");
  await expect(page.locator(".sr-observation")).toHaveCount(7);
  await page
    .getByLabel("Filtrer les observations par qualité", { exact: true })
    .selectOption("too_small");
  await expect(page.locator(".sr-observation")).toHaveCount(1);
});

test("validation confirmée, attribution et statut fictifs sans stockage ni API", async ({
  page,
}) => {
  await open(page);
  const calls: string[] = [];
  page.on("request", (request) => {
    if (new URL(request.url()).pathname.startsWith("/api"))
      calls.push(request.url());
  });
  const storage = await page.evaluate(() => ({
    local: JSON.stringify(localStorage),
    session: JSON.stringify(sessionStorage),
  }));
  await card(page, 1).getByRole("checkbox").check();
  await card(page, 2).getByRole("checkbox").check();
  const validate = page.getByRole("button", {
    name: "Valider la sélection",
    exact: true,
  });
  await expect(validate).toBeDisabled();
  await page
    .getByLabel("Espèce à attribuer", { exact: true })
    .selectOption("renard");
  await validate.click();
  const dialog = page.getByRole("dialog", {
    name: "Valider la sélection",
    exact: true,
  });
  await expect(dialog).toContainText("validation fictive de 2 observations");
  await expect(page.locator(".sr-observation-meta .sv-status")).toHaveCount(0);
  await dialog.getByRole("button", { name: "Annuler", exact: true }).click();
  await expect(selectionCount(page)).toHaveText("2 sélectionnées");
  await validate.click();
  await page
    .getByRole("button", { name: "Confirmer la validation", exact: true })
    .click();
  await expect(page.locator(".sr-feedback")).toContainText(
    "2 observations validées comme « renard »",
  );
  await expect(selectionCount(page)).toHaveText("0 sélectionnée");
  for (const number of [1, 2]) {
    await expect(card(page, number).getByRole("heading")).toHaveText("renard");
    await expect(card(page, number).locator(".sv-status")).toHaveText(
      "Validée",
    );
  }
  await expect(card(page, 1).locator(".sr-observation-filename")).toHaveText(
    "Chevreuil-Score-271.mp4",
  );
  await expect(card(page, 6).locator(".sr-review-status")).toHaveText(
    "À revoir",
  );
  await page
    .getByLabel("Filtrer les observations par espèce", { exact: true })
    .selectOption("renard");
  await expect(page.locator(".sr-observation")).toHaveCount(2);
  expect(
    await page.evaluate(() => ({
      local: JSON.stringify(localStorage),
      session: JSON.stringify(sessionStorage),
    })),
  ).toEqual(storage);
  await page.reload();
  await expect(page.locator(".sr-observation")).toHaveCount(8);
  await expect(page.locator(".sr-observation-meta .sv-status")).toHaveCount(0);
  expect(calls).toEqual([]);
});

test("retrait uniquement après confirmation, test protégé conservé et rechargement réversible", async ({
  page,
}) => {
  await open(page);
  await allCheckbox(page).check();
  await page
    .getByRole("button", { name: "Effacer la sélection", exact: true })
    .click();
  const dialog = page.getByRole("dialog", {
    name: "Effacer la sélection",
    exact: true,
  });
  await expect(dialog).toContainText("Aucun fichier réel ne sera supprimé.");
  await dialog.getByRole("button", { name: "Annuler", exact: true }).click();
  await expect(page.locator(".sr-observation")).toHaveCount(8);
  await expect(selectionCount(page)).toHaveText("6 sélectionnées");
  await page
    .getByRole("button", { name: "Effacer la sélection", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Confirmer le retrait simulé", exact: true })
    .click();
  await expect(page.locator(".sr-feedback")).toContainText(
    "6 observations retirées de la liste locale",
  );
  await expect(page.locator(".sr-observation")).toHaveCount(2);
  await expect(page.locator(".sr-observation.is-protected")).toHaveCount(2);
  await expect(allCheckbox(page)).toBeDisabled();
  await expect(selectionCount(page)).toHaveText("0 sélectionnée");
  await page.reload();
  await expect(page.locator(".sr-observation")).toHaveCount(8);
});

test("aperçu statique et lecteur local réutilisé, fermeture arrête la lecture", async ({
  page,
}) => {
  await open(page);
  await card(page, 1).getByRole("button").click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toContainText("Aperçu statique de démonstration");
  await expect(dialog.locator(".sa-player video")).toHaveCount(0);
  await expect(dialog.locator(".sa-player-demo")).toHaveText(
    "IMAGE FIXE · LECTURE SIMULÉE",
  );
  await dialog
    .getByRole("button", { name: "Démarrer la lecture simulée", exact: true })
    .click();
  await expect(dialog.locator(".sa-player-time")).not.toHaveText("0:00 / 0:27");
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await card(page, 6).getByRole("button").click();
  await expect(dialog).toContainText("Image de test protégée");
  await dialog
    .getByRole("button", { name: "Fermer la fenêtre", exact: true })
    .click();
  await card(page, 8).getByRole("button").click();
  const video = dialog.locator(".sa-player video");
  await expect
    .poll(() =>
      video.evaluate((element) => (element as HTMLVideoElement).videoHeight),
    )
    .toBe(1920);
  await dialog
    .getByRole("button", { name: "Lire la vidéo locale", exact: true })
    .click();
  await expect
    .poll(() =>
      video.evaluate((element) => (element as HTMLVideoElement).currentTime),
    )
    .toBeGreaterThan(0.25);
  await dialog
    .getByRole("button", { name: "Fermer la fenêtre", exact: true })
    .click();
  await expect(page.locator(".sa-player")).toHaveCount(0);
  expect(
    await page
      .locator("video")
      .evaluateAll((elements) =>
        elements.every((element) => (element as HTMLVideoElement).paused),
      ),
  ).toBe(true);
});

test("colonnes adaptées sur tablette et mobile, actions utilisables au clavier", async ({
  page,
}, info) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await open(page);
  for (const [width, columns] of [
    [1280, 3],
    [1000, 2],
    [390, 1],
  ]) {
    await page.setViewportSize({ width, height: 844 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    expect(
      await page
        .locator(".sr-observation-grid")
        .evaluate(
          (element) =>
            getComputedStyle(element).gridTemplateColumns.split(" ").length,
        ),
    ).toBe(columns);
  }
  await card(page, 1).getByRole("checkbox").focus();
  await page.keyboard.press("Space");
  await expect(selectionCount(page)).toHaveText("1 sélectionnée");
  await page
    .getByLabel("Espèce à attribuer", { exact: true })
    .selectOption("chevreuil");
  await page
    .getByRole("button", { name: "Valider la sélection", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Confirmer la validation", exact: true })
    .focus();
  await page.keyboard.press("Enter");
  await expect(card(page, 1).locator(".sv-status")).toHaveText("Validée");
  await ready(page);
  await page.screenshot({
    path: info.outputPath("validation-mobile.png"),
    fullPage: true,
  });
  for (const path of [
    "/documents",
    "/",
    "/videos",
    "/parcelles",
    "/analyses",
    "/review",
  ]) {
    await page.locator(`.sym-wheel-link[data-section="${path}"]`).click();
    await expect(
      page.locator('.sym-wheel-link[aria-current="page"]'),
    ).toHaveAttribute("data-section", path);
    await expect(
      page.locator('.sym-wheel-link[aria-current="page"]'),
    ).toHaveAttribute("data-slot", "4");
  }
});
