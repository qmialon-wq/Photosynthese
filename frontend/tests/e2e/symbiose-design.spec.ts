import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
const sections = [
  { path: "/", label: "Accueil" },
  { path: "/videos", label: "Vidéothèque" },
  { path: "/parcelles", label: "Mes dossiers" },
  { path: "/analyses", label: "Analyses" },
  { path: "/review", label: "Validation humaine" },
  { path: "/documents", label: "Documents scientifiques" },
];
test.use({ viewport: { width: 1600, height: 900 } });

test("Accueil à 1600 × 900, sans backend et avec des composants accessibles", async ({
  page,
}, testInfo) => {
  const requests: string[] = [];
  page.on("request", (request) => {
    if (new URL(request.url()).pathname.startsWith("/api"))
      requests.push(request.url());
  });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Accueil Symbiose" }),
  ).toHaveCount(1);
  await expect(page.locator(".sym-stat")).toHaveCount(4);
  await expect(page.locator(".sym-journey-card")).toHaveCount(3);
  await expect(page.locator(".sym-analysis-row")).toHaveCount(3);
  await expect(page.locator(".sym-latest")).toBeInViewport({ ratio: 1 });
  await expect(
    page.getByRole("button", { name: "Paramètres", exact: true }),
  ).toBeInViewport();
  await page.evaluate(async () => {
    await document.fonts.ready;
    await Promise.all(
      [...document.images].map((image) => image.decode().catch(() => {})),
    );
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
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
  await page.screenshot({
    path: testInfo.outputPath("accueil-1600x900.png"),
    fullPage: true,
  });
  expect(requests).toEqual([]);
});

test("les six rubriques tournent vers l’emplacement quatre et les icônes restent droites", async ({
  page,
}, testInfo) => {
  const requests: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/api/")) requests.push(request.url());
  });
  await page.goto("/");
  const nav = page.getByRole("navigation", { name: "Navigation principale" });
  await expect(nav.getByRole("link")).toHaveCount(6);
  const arc = await page.locator(".sym-wheel-arc path").getAttribute("d");
  const fixedPositions = new Map<number, { left: number; top: number }>();
  for (let active = 0; active < sections.length; active++) {
    const section = sections[active];
    await nav.getByRole("link", { name: section.label, exact: true }).click();
    await expect(page).toHaveURL(
      new RegExp(`${section.path === "/" ? "/" : section.path}$`),
    );
    await expect(nav.locator('[aria-current="page"]')).toHaveAttribute(
      "data-slot",
      "4",
    );
    await expect(nav.locator('[aria-current="page"]')).toHaveAttribute(
      "aria-label",
      section.label,
    );
    const canvas = await page.locator(".sym-canvas").boundingBox();
    expect(canvas?.x).toBe(0);
    expect(canvas?.y).toBe(0);
    expect(canvas?.width).toBe(1600);
    expect(canvas?.height).toBeGreaterThanOrEqual(900);
    // Attendre la fin effective des transitions pour comparer les positions finales.
    await page.evaluate(async () => {
      await Promise.all(
        document
          .getAnimations()
          .map((animation) => animation.finished.catch(() => {})),
      );
    });
    for (let index = 0; index < sections.length; index++) {
      const link = nav.getByRole("link", {
        name: sections[index].label,
        exact: true,
      });
      const slot = ((index - active + 9) % 6) + 1;
      await expect(link).toHaveAttribute("data-slot", String(slot));
      const values = await link.evaluate((element) => {
        const style = getComputedStyle(element);
        return {
          left: parseFloat(style.left),
          top: parseFloat(style.top),
          transform: getComputedStyle(element.querySelector("svg")!).transform,
        };
      });
      expect(values.transform).toBe("none");
      if (!fixedPositions.has(slot)) fixedPositions.set(slot, values);
      expect(values.left).toBeCloseTo(fixedPositions.get(slot)!.left, 1);
      expect(values.top).toBeCloseTo(fixedPositions.get(slot)!.top, 1);
    }
    expect(await page.locator(".sym-wheel-arc path").getAttribute("d")).toBe(
      arc,
    );
    if (active === 5) {
      await page.mouse.move(0, 0);
      await page.screenshot({
        path: testInfo.outputPath("roue-documents.png"),
      });
    }
  }
  await page.goBack();
  await expect(nav.locator('[aria-current="page"]')).toHaveAttribute(
    "aria-label",
    "Validation humaine",
  );
  await page.reload();
  await expect(nav.locator('[aria-current="page"]')).toHaveAttribute(
    "data-slot",
    "4",
  );
  expect(requests).toEqual([]);
});

test("actions et navigation au clavier", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Rechercher", exact: true }).click();
  await expect(page.getByRole("searchbox")).toBeFocused();
  await page.getByRole("searchbox").fill("vidéo");
  await page
    .locator(".sym-action-panel")
    .getByRole("link", { name: "Vidéothèque" })
    .click();
  await expect(page).toHaveURL(/\/videos$/);
  await page.getByRole("button", { name: "Paramètres", exact: true }).click();
  await page.getByLabel("Réduire les animations").check();
  const nav = page.getByRole("navigation", { name: "Navigation principale" });
  expect(
    await nav
      .getByRole("link", { name: "Accueil", exact: true })
      .evaluate((element) => getComputedStyle(element).transitionDuration),
  ).toBe("0s");
  await page.keyboard.press("Escape");
  await expect(
    page.getByRole("button", { name: "Paramètres", exact: true }),
  ).toBeFocused();
  await nav.getByRole("link", { name: "Accueil", exact: true }).focus();
  await page.keyboard.press("ArrowDown");
  await expect(
    nav.getByRole("link", { name: "Vidéothèque", exact: true }),
  ).toBeFocused();
});

test("la roue reste utilisable sur mobile et respecte les mouvements réduits", async ({
  page,
}, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  const canvas = await page.locator(".sym-canvas").boundingBox();
  expect(canvas?.x).toBe(0);
  expect(canvas?.y).toBe(0);
  expect(canvas?.width).toBe(390);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  const nav = page.getByRole("navigation", { name: "Navigation principale" });
  for (const section of [...sections].reverse()) {
    await nav.getByRole("link", { name: section.label, exact: true }).click();
    await expect(nav.locator('[aria-current="page"]')).toHaveAttribute(
      "aria-label",
      section.label,
    );
  }
  await page.screenshot({
    path: testInfo.outputPath("accueil-mobile.png"),
    fullPage: true,
  });
});
