import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test.use({ viewport: { width: 1600, height: 900 } });
async function ready(page: Page) {
  await page.mouse.move(0, 0);
  await page.evaluate(async () => {
    await document.fonts.ready;
    await Promise.all(
      Array.from(document.images).map((i) => i.decode().catch(() => {})),
    );
    await Promise.all(
      Array.from(
        document.querySelectorAll(
          ".sym-photo,.sym-forest,.sf-project-photo,.sa-poster",
        ),
      ).map(
        (e) =>
          new Promise<void>((resolve, reject) => {
            const url = getComputedStyle(e).backgroundImage.match(
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
      document.getAnimations().map((a) => a.finished.catch(() => {})),
    );
  });
}
async function wheel(page: Page) {
  return page.locator(".sym-wheel-link").evaluateAll((es) =>
    es.map((e) => {
      const s = getComputedStyle(e),
        box = e.getBoundingClientRect();
      return {
        section: e.getAttribute("aria-label"),
        slot: e.getAttribute("data-slot"),
        x: box.x,
        y: box.y,
        width: box.width,
        height: box.height,
        color: s.color,
        background: s.backgroundImage,
        border: s.border,
        shadow: s.boxShadow,
        font: getComputedStyle(e.querySelector(".sym-wheel-label")!).font,
        icon: Array.from(e.querySelectorAll("svg path")).map((p) =>
          p.getAttribute("d"),
        ),
      };
    }),
  );
}
async function aligned(
  page: Page,
  expected = { x: 0.645, y: 0.36, width: 0.285, height: 0.395 },
) {
  const surface = await page.locator(".sa-media-surface").boundingBox();
  const box = await page.locator(".sa-detection").boundingBox();
  expect(surface).not.toBeNull();
  expect(box).not.toBeNull();
  expect((box!.x - surface!.x) / surface!.width).toBeCloseTo(expected.x, 2);
  expect((box!.y - surface!.y) / surface!.height).toBeCloseTo(expected.y, 2);
  expect(box!.width / surface!.width).toBeCloseTo(expected.width, 2);
  expect(box!.height / surface!.height).toBeCloseTo(expected.height, 2);
}
async function range(page: Page, label: string, value: number) {
  await page.getByLabel(label, { exact: true }).evaluate((element, next) => {
    (element as HTMLInputElement).value = String(next);
    element.dispatchEvent(new Event("input", { bubbles: true }));
  }, value);
}
async function open(page: Page) {
  await page.goto("/analyses");
  await page.locator(".sa-player").waitFor();
  await ready(page);
}

test("quatre captures, panneaux accessibles et navigation commune sans régression", async ({
  page,
}, info) => {
  test.setTimeout(90000);
  const calls: string[] = [],
    errors: string[] = [];
  page.on("request", (r) => {
    if (new URL(r.url()).pathname.startsWith("/api")) calls.push(r.url());
  });
  page.on("pageerror", (e) => errors.push(e.message));
  const snapshots = new Map<
    string,
    { image: Buffer; wheel: Awaited<ReturnType<typeof wheel>> }
  >();
  const routes = [
    { path: "/", name: "accueil", selector: ".sym-home" },
    { path: "/videos", name: "videotheque", selector: ".sv-video-card" },
    { path: "/parcelles", name: "mes-dossiers", selector: ".sf-project-card" },
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
  await page.locator('.sym-wheel-link[data-section="/analyses"]').click();
  await page.locator(".sa-player").waitFor();
  await ready(page);
  const state = await wheel(page);
  expect(
    state
      .slice()
      .sort((a, b) => Number(a.slot) - Number(b.slot))
      .map((e) => e.section),
  ).toEqual([
    "Accueil",
    "Vidéothèque",
    "Mes dossiers",
    "Analyses",
    "Validation humaine",
    "Documents scientifiques",
  ]);
  const active = state.find((e) => e.slot === "4")!;
  const homeActive = snapshots.get("/")!.wheel.find((e) => e.slot === "4")!;
  expect({ ...active, section: "", icon: [] }).toEqual({
    ...homeActive,
    section: "",
    icon: [],
  });
  expect(await page.locator(".sym-wheel-arc path").getAttribute("d")).toBe(arc);
  await expect(page.locator(".sa-page")).toBeInViewport({ ratio: 1 });
  const left = await page.locator(".sa-video-panel").boundingBox(),
    right = await page.locator(".sa-settings").boundingBox();
  expect(left!.y).toBe(right!.y);
  expect(left!.x + left!.width).toBeLessThan(right!.x);
  await aligned(page);
  await expect(page.locator(".sa-detection-label")).toHaveText(
    "Chevreuil · 0,94",
  );
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
    path: info.outputPath("analyse-video-1600x900.png"),
  });
  for (const route of routes) {
    await page.locator(`.sym-wheel-link[data-section="${route.path}"]`).click();
    await page.locator(route.selector).first().waitFor();
    await ready(page);
    expect(await wheel(page)).toEqual(snapshots.get(route.path)!.wheel);
    const after = await page.screenshot({
      mask: [page.locator(".sym-wheel-link"), page.locator(".sym-demo-note")],
    });
    expect(after.equals(snapshots.get(route.path)!.image)).toBe(true);
  }
  expect(calls).toEqual([]);
  expect(errors).toEqual([]);
});

test("aperçu honnête : lecture simulée, position, volume et plein écran", async ({
  page,
}) => {
  await open(page);
  await expect(page.locator(".sa-player video")).toHaveCount(0);
  await expect(page.locator(".sa-player-demo")).toHaveText(
    "IMAGE FIXE · LECTURE SIMULÉE",
  );
  await page
    .getByRole("button", { name: "Démarrer la lecture simulée", exact: true })
    .click();
  await expect(page.locator(".sa-player-time")).not.toHaveText("0:00 / 0:33");
  await page
    .getByRole("button", {
      name: "Mettre la lecture simulée en pause",
      exact: true,
    })
    .click();
  await range(page, "Position de lecture", 16);
  await expect(page.locator(".sa-player-time")).toHaveText("0:16 / 0:33");
  await page
    .getByRole("button", { name: "Régler le volume", exact: true })
    .click();
  await range(page, "Volume", 0.25);
  await expect(page.getByLabel("Volume", { exact: true })).toHaveValue("0.25");
  await page
    .getByRole("button", { name: "Couper le son", exact: true })
    .click();
  await expect(page.getByLabel("Volume", { exact: true })).toHaveValue("0");
  await page
    .getByRole("button", { name: "Passer en plein écran", exact: true })
    .click();
  await expect
    .poll(() => page.evaluate(() => !!document.fullscreenElement))
    .toBe(true);
  await aligned(page);
  await page
    .getByRole("button", { name: "Quitter le plein écran", exact: true })
    .click();
  await expect
    .poll(() => page.evaluate(() => !!document.fullscreenElement))
    .toBe(false);
});

test("réglages, progression fictive et préparation sans extraction", async ({
  page,
}) => {
  await open(page);
  const calls: string[] = [];
  page.on("request", (r) => {
    if (new URL(r.url()).pathname.startsWith("/api")) calls.push(r.url());
  });
  await page
    .getByLabel("Objectif de l’analyse", { exact: true })
    .selectOption("presence");
  await page
    .getByLabel("Niveau de détail", { exact: true })
    .selectOption("balanced");
  await expect(page.locator(".sa-setting-block").last()).toContainText(
    "Le mode équilibré",
  );
  await page
    .getByRole("button", { name: "Lancer l’analyse", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Analyse en cours…", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByLabel("Niveau de détail", { exact: true }),
  ).toBeDisabled();
  await expect(page.locator(".sa-detection")).toHaveCount(0);
  await expect(page.getByRole("progressbar")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Choisir une vidéo", exact: true }),
  ).toBeDisabled();
  await expect(page.locator(".sa-analysis-completed")).toContainText(
    "Analyse terminée",
  );
  await aligned(page);
  await page
    .getByRole("button", {
      name: "Préparer les recadrages à valider",
      exact: true,
    })
    .click();
  await expect(page.getByRole("dialog")).toContainText(
    "Aucun recadrage n’est extrait ni enregistré.",
  );
  await page.getByRole("button", { name: "J’ai compris", exact: true }).click();
  await page
    .getByLabel("Niveau de détail", { exact: true })
    .selectOption("fine");
  await expect(page.locator(".sa-analysis-completed")).toHaveCount(0);
  expect(calls).toEqual([]);
});

test("sélection fictive et véritable lecture du fichier local portrait", async ({
  page,
}) => {
  await open(page);
  await page
    .getByRole("button", { name: "Choisir une vidéo", exact: true })
    .click();
  await page
    .getByRole("button", {
      name: "Sélectionner Renard-Scene-018.mp4",
      exact: true,
    })
    .click();
  await expect(page.locator(".sa-detection-label")).toHaveText("Renard · 0,91");
  await expect(page.locator("#sa-filename")).toHaveText("Renard-Scene-018.mp4");
  await page
    .getByRole("button", { name: "Choisir une vidéo", exact: true })
    .click();
  await page
    .getByRole("button", {
      name: "Sélectionner 19136320-hd_1080_1920_50fps.mp4",
      exact: true,
    })
    .click();
  const video = page.locator(".sa-player video");
  await expect
    .poll(() => video.evaluate((v) => (v as HTMLVideoElement).videoHeight))
    .toBe(1920);
  await expect(page.locator(".sa-player-demo")).toHaveText(
    "VIDÉO LOCALE · DÉTECTION SIMULÉE",
  );
  await aligned(page, { x: 0.24, y: 0.36, width: 0.54, height: 0.28 });
  const player = await page.locator(".sa-player").boundingBox(),
    surface = await page.locator(".sa-media-surface").boundingBox();
  expect(surface!.width / surface!.height).toBeCloseTo(1080 / 1920, 2);
  expect(surface!.x).toBeGreaterThan(player!.x + player!.width * 0.3);
  await page
    .getByRole("button", { name: "Lire la vidéo locale", exact: true })
    .click();
  await expect
    .poll(() => video.evaluate((v) => (v as HTMLVideoElement).currentTime))
    .toBeGreaterThan(0.25);
  await page
    .getByRole("button", {
      name: "Mettre la vidéo locale en pause",
      exact: true,
    })
    .click();
  await page
    .getByRole("button", { name: "Régler le volume", exact: true })
    .click();
  await range(page, "Volume", 0.25);
  await expect
    .poll(() => video.evaluate((v) => (v as HTMLVideoElement).volume))
    .toBe(0.25);
  await range(page, "Position de lecture", 3);
  await expect
    .poll(() => video.evaluate((v) => (v as HTMLVideoElement).currentTime))
    .toBeCloseTo(3, 1);
  await expect(page.getByRole("alert")).toHaveCount(0);
});

test("mobile, cadre relatif et retour vers les six rubriques", async ({
  page,
}, info) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await open(page);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await aligned(page);
  const left = await page.locator(".sa-video-panel").boundingBox(),
    right = await page.locator(".sa-settings").boundingBox();
  expect(right!.y).toBeGreaterThan(left!.y + left!.height);
  await page.screenshot({
    path: info.outputPath("analyse-mobile.png"),
    fullPage: true,
  });
  for (const path of [
    "/review",
    "/documents",
    "/",
    "/videos",
    "/parcelles",
    "/analyses",
  ]) {
    await page.locator(`.sym-wheel-link[data-section="${path}"]`).click();
    await expect(
      page.locator('.sym-wheel-link[aria-current="page"]'),
    ).toHaveAttribute("data-section", path);
    await expect(
      page.locator('.sym-wheel-link[aria-current="page"]'),
    ).toHaveAttribute("data-slot", "4");
  }
  await aligned(page);
});
