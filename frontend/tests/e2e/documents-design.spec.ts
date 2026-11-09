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
  await page.goto("/documents");
  await page.locator(".sd-corpus").waitFor();
  await ready(page);
}
const corpusSpecies = (page: Page) =>
  page.getByLabel("Espèce du corpus", { exact: true });
const all = (page: Page) =>
  page.getByRole("checkbox", {
    name: "Tout sélectionner sur cette page",
    exact: true,
  });
const remove = (page: Page) =>
  page.getByRole("button", { name: "Retirer du corpus", exact: true });
async function finishRetrieval(page: Page) {
  await page.clock.fastForward(700);
  await expect(page.locator(".sd-task-status")).toHaveText("En cours");
  for (let step = 0; step < 6; step++) await page.clock.fastForward(350);
  await expect(page.locator(".sd-task-status")).toHaveText("Terminé");
}

test("six captures, états vides fidèles, roue et cinq pages sans régression", async ({
  page,
}, info) => {
  test.setTimeout(150000);
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
    {
      path: "/review",
      name: "validation-humaine",
      selector: ".sr-observation",
    },
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
  await page.locator('.sym-wheel-link[data-section="/documents"]').click();
  await page.locator(".sd-corpus").waitFor();
  await ready(page);
  const state = await wheel(page),
    active = state.find((item) => item.slot === "4")!,
    home = snapshots.get("/")!.wheel.find((item) => item.slot === "4")!;
  expect(
    state
      .slice()
      .sort((a, b) => Number(a.slot) - Number(b.slot))
      .map((item) => item.section),
  ).toEqual([
    "Mes dossiers",
    "Analyses",
    "Validation humaine",
    "Documents scientifiques",
    "Accueil",
    "Vidéothèque",
  ]);
  expect({ ...active, section: "", font: "", icon: [] }).toEqual({
    ...home,
    section: "",
    font: "",
    icon: [],
  });
  expect(active.width).toBe(186);
  expect(active.height).toBe(62);
  expect(await page.locator(".sym-wheel-arc path").getAttribute("d")).toBe(arc);
  const label = page.locator(
    '.sym-wheel-link[aria-current="page"] .sym-wheel-label',
  );
  expect(
    await label.evaluate(
      (element) => element.scrollWidth <= element.clientWidth + 1,
    ),
  ).toBe(true);
  await expect(page.locator(".sd-page")).toBeInViewport({ ratio: 1 });
  await expect(corpusSpecies(page)).toHaveValue("renard");
  await expect(corpusSpecies(page).locator("option:checked")).toHaveText(
    "Renard · 0 documents",
  );
  await expect(page.locator(".sd-document-card")).toHaveCount(0);
  await expect(all(page)).toBeDisabled();
  await expect(remove(page)).toBeDisabled();
  await expect(page.locator(".sd-selection-count")).toHaveText(
    "0 sélectionné(s)",
  );
  await expect(page.locator(".sd-corpus .sd-empty-state")).toHaveText(
    "Aucun document téléchargé pour cette espèce. Lancez une récupération ou importez un fichier.",
  );
  await expect(page.locator(".sd-progress-panel")).toContainText(
    "Aucune récupération en cours.",
  );
  await expect(
    page.getByRole("button", { name: "Page précédente", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Page suivante", exact: true }),
  ).toBeDisabled();
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
    path: info.outputPath("documents-scientifiques-1600x900.png"),
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

test("espèces, pagination, sélection limitée à la page et consultation fictive", async ({
  page,
}) => {
  await open(page);
  await corpusSpecies(page).selectOption("chevreuil");
  await expect(corpusSpecies(page).locator("option:checked")).toHaveText(
    "Chevreuil · 5 documents",
  );
  await expect(page.locator(".sd-document-card")).toHaveCount(2);
  await page.locator(".sd-document-card input").first().check();
  expect(
    await all(page).evaluate(
      (input) => (input as HTMLInputElement).indeterminate,
    ),
  ).toBe(true);
  await all(page).check();
  await expect(page.locator(".sd-selection-count")).toHaveText(
    "2 sélectionné(s)",
  );
  await page
    .getByRole("button", { name: "Page suivante", exact: true })
    .click();
  await expect(page.locator(".sv-page-current")).toHaveText("Page 2");
  await expect(page.locator(".sd-selection-count")).toHaveText(
    "0 sélectionné(s)",
  );
  await page
    .getByRole("button", { name: "Page suivante", exact: true })
    .click();
  await expect(page.locator(".sd-document-card")).toHaveCount(1);
  await expect(
    page.getByRole("button", { name: "Page suivante", exact: true }),
  ).toBeDisabled();
  await page.locator(".sd-document-card button").click();
  await expect(page.getByRole("dialog")).toContainText(
    "Cette entrée est fictive.",
  );
  await expect(page.getByRole("dialog").getByRole("link")).toHaveCount(0);
  await page
    .getByRole("button", { name: "Fermer la fenêtre", exact: true })
    .click();
  await all(page).check();
  await corpusSpecies(page).selectOption("sanglier");
  await expect(page.locator(".sv-page-current")).toHaveText("Page 1");
  await expect(page.locator(".sd-selection-count")).toHaveText(
    "0 sélectionné(s)",
  );
});

test("retrait confirmé, compteurs et retour à l’état vide sans suppression réelle", async ({
  page,
}) => {
  await open(page);
  await corpusSpecies(page).selectOption("sanglier");
  await all(page).check();
  await remove(page).click();
  const dialog = page.getByRole("dialog", {
    name: "Retirer du corpus",
    exact: true,
  });
  await expect(dialog).toContainText("Aucun fichier réel ne sera supprimé.");
  await dialog.getByRole("button", { name: "Annuler", exact: true }).click();
  await expect(page.locator(".sd-document-card")).toHaveCount(2);
  await expect(page.locator(".sd-selection-count")).toHaveText(
    "2 sélectionné(s)",
  );
  await remove(page).click();
  await page
    .getByRole("button", { name: "Confirmer le retrait simulé", exact: true })
    .click();
  await expect(page.locator(".sd-document-card")).toHaveCount(0);
  await expect(corpusSpecies(page).locator("option:checked")).toHaveText(
    "Sanglier · 0 documents",
  );
  await expect(remove(page)).toBeDisabled();
  await expect(page.locator(".sd-feedback")).toContainText(
    "Aucun fichier réel n’a été supprimé.",
  );
  await corpusSpecies(page).selectOption("chevreuil");
  await page
    .getByRole("button", { name: "Page suivante", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Page suivante", exact: true })
    .click();
  await all(page).check();
  await remove(page).click();
  await page
    .getByRole("button", { name: "Confirmer le retrait simulé", exact: true })
    .click();
  await expect(page.locator(".sv-page-current")).toHaveText("Page 2");
  await expect(page.locator(".sd-document-card")).toHaveCount(2);
  await page.reload();
  await corpusSpecies(page).selectOption("sanglier");
  await expect(page.locator(".sd-document-card")).toHaveCount(2);
});

test("choix multiple annulable, progression des espèces choisies et exemples explicites", async ({
  page,
}) => {
  await open(page);
  await page.clock.install();
  await page
    .getByRole("button", { name: "Choisir les espèces", exact: true })
    .click();
  let dialog = page.getByRole("dialog", {
    name: "Choisir les espèces",
    exact: true,
  });
  await dialog.getByRole("checkbox", { name: "Renard", exact: true }).uncheck();
  await dialog.getByRole("button", { name: "Annuler", exact: true }).click();
  await page
    .getByRole("button", { name: "Choisir les espèces", exact: true })
    .click();
  dialog = page.getByRole("dialog", {
    name: "Choisir les espèces",
    exact: true,
  });
  await expect(
    dialog.getByRole("checkbox", { name: "Renard", exact: true }),
  ).toBeChecked();
  for (const checkbox of await dialog.getByRole("checkbox").all())
    await checkbox.uncheck();
  await expect(
    dialog.getByRole("button", { name: "Confirmer", exact: true }),
  ).toBeDisabled();
  await dialog
    .getByRole("checkbox", { name: "Chevreuil", exact: true })
    .check();
  await dialog.getByRole("checkbox", { name: "Blaireau", exact: true }).check();
  await dialog.getByRole("button", { name: "Confirmer", exact: true }).click();
  await expect(page.locator(".sd-task-status")).toHaveText("En attente");
  await expect(
    page.getByRole("button", {
      name: "Récupérer pour toutes les espèces",
      exact: true,
    }),
  ).toBeDisabled();
  await finishRetrieval(page);
  await expect(page.locator(".sd-task-heading")).toContainText("2 espèces");
  await expect(page.locator(".sd-task-note")).toContainText(
    "Aucun article recherché ou téléchargé.",
  );
  await expect(corpusSpecies(page).locator("option:checked")).toHaveText(
    "Renard · 0 documents",
  );
  await corpusSpecies(page).selectOption("chevreuil");
  await expect(corpusSpecies(page).locator("option:checked")).toHaveText(
    "Chevreuil · 6 documents",
  );
  await page
    .getByRole("button", { name: "Choisir les espèces", exact: true })
    .click();
  await expect(
    page
      .getByRole("dialog")
      .getByRole("checkbox", { name: "Renard", exact: true }),
  ).not.toBeChecked();
});

test("récupération globale confirmée sans réseau ni stockage et arrêt en quittant la page", async ({
  page,
}) => {
  await open(page);
  await page.clock.install();
  const calls: string[] = [],
    errors: string[] = [];
  page.on("request", (request) => calls.push(request.url()));
  page.on("pageerror", (error) => errors.push(error.message));
  const storage = await page.evaluate(() => ({
    local: JSON.stringify(localStorage),
    session: JSON.stringify(sessionStorage),
  }));
  const retrieve = page.getByRole("button", {
    name: "Récupérer pour toutes les espèces",
    exact: true,
  });
  await retrieve.click();
  await expect(page.getByRole("dialog")).toContainText("5 espèces");
  await page.getByRole("button", { name: "Annuler", exact: true }).click();
  await expect(page.locator(".sd-task")).toHaveCount(0);
  await retrieve.click();
  await page
    .getByRole("button", { name: "Confirmer la simulation", exact: true })
    .click();
  await expect(page.locator(".sd-task-status")).toHaveText("En attente");
  await finishRetrieval(page);
  await expect(page.getByRole("progressbar")).toHaveAttribute("value", "100");
  await expect(corpusSpecies(page).locator("option:checked")).toHaveText(
    "Renard · 1 document",
  );
  await expect(page.locator(".sd-document-card h3")).toContainText(
    "Exemple fictif",
  );
  expect(
    await page.evaluate(() => ({
      local: JSON.stringify(localStorage),
      session: JSON.stringify(sessionStorage),
    })),
  ).toEqual(storage);
  expect(calls).toEqual([]);
  await retrieve.click();
  await page
    .getByRole("button", { name: "Confirmer la simulation", exact: true })
    .click();
  await page.locator('.sym-wheel-link[data-section="/"]').click();
  await page.clock.fastForward(10000);
  await page.locator('.sym-wheel-link[data-section="/documents"]').click();
  await expect(page.locator(".sd-task")).toHaveCount(0);
  // Le corpus partagé conserve la première récupération achevée ; la seconde a été annulée.
  await expect(corpusSpecies(page).locator("option:checked")).toHaveText(
    "Renard · 1 document",
  );
  expect(errors).toEqual([]);
});

test("sélecteur local, nom du fichier sans lecture, import annulable et extensions prévues", async ({
  page,
}) => {
  await open(page);
  const calls: string[] = [];
  page.on("request", (request) => calls.push(request.url()));
  const picker = page.waitForEvent("filechooser");
  await page
    .getByRole("button", { name: "Importer un document", exact: true })
    .click();
  await (
    await picker
  ).setFiles({
    name: "Étude locale.PDF",
    mimeType: "application/pdf",
    buffer: Buffer.from("Fichier de test sans contenu scientifique"),
  });
  await expect(page.getByRole("dialog")).toContainText("Étude locale.PDF");
  await expect(page.locator(".sd-document-card")).toHaveCount(0);
  await page.getByRole("button", { name: "Annuler", exact: true }).click();
  const input = page.locator('input[type="file"]');
  await input.setInputFiles({
    name: "article.pdf.exe",
    mimeType: "application/octet-stream",
    buffer: Buffer.from("test"),
  });
  await expect(page.getByRole("alert")).toContainText("PDF, DOCX ou TXT");
  await expect(page.locator(".sd-document-card")).toHaveCount(0);
  await input.setInputFiles({
    name: "Notes locales.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("Texte qui ne doit pas être analysé"),
  });
  await page
    .getByRole("button", {
      name: "Ajouter l’entrée de démonstration",
      exact: true,
    })
    .click();
  await expect(page.getByRole("alert")).toHaveCount(0);
  await expect(corpusSpecies(page).locator("option:checked")).toHaveText(
    "Renard · 1 document",
  );
  await expect(page.locator(".sd-document-card h3")).toHaveText(
    "Import simulé — Notes locales.txt",
  );
  await expect(page.locator(".sd-feedback").first()).toContainText(
    "Aucun contenu de fichier n’a été lu",
  );
  expect(calls).toEqual([]);
  await page.reload();
  await expect(page.locator(".sd-document-card")).toHaveCount(0);
});

test("responsive, clavier et six rubriques accessibles", async ({
  page,
}, info) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await open(page);
  for (const width of [1280, 1000, 390]) {
    await page.setViewportSize({ width, height: 844 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  }
  await corpusSpecies(page).selectOption("chevreuil");
  await page.locator(".sd-document-card input").first().focus();
  await page.keyboard.press("Space");
  await expect(page.locator(".sd-selection-count")).toHaveText(
    "1 sélectionné(s)",
  );
  await remove(page).click();
  await page.getByRole("button", { name: "Annuler", exact: true }).focus();
  await page.keyboard.press("Enter");
  await corpusSpecies(page).selectOption("renard");
  await page.locator(".sd-progress-panel").scrollIntoViewIfNeeded();
  await ready(page);
  await page.screenshot({
    path: info.outputPath("documents-mobile.png"),
    fullPage: true,
  });
  for (const path of [
    "/",
    "/videos",
    "/parcelles",
    "/analyses",
    "/review",
    "/documents",
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
