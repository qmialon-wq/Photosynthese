import { test, expect } from "@playwright/test";

const routes = [
  "/",
  "/videos",
  "/parcelles",
  "/analyses",
  "/review",
  "/documents",
];

for (const viewport of [
  { width: 1920, height: 1080 },
  { width: 1600, height: 900 },
  { width: 1440, height: 900 },
  { width: 1280, height: 800 },
  { width: 390, height: 844 },
]) {
  test(`cadre commun et six configurations à ${viewport.width} × ${viewport.height}`, async ({
    page,
  }) => {
    await page.setViewportSize(viewport);
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/");
    await page.locator(".sym-home").waitFor();
    const geometry = () =>
      page.evaluate(() => {
        const selectors = [
          ".sym-brand",
          ".sym-header-actions",
          ".sym-wheel",
          ".sym-wheel-arc",
          ".sym-settings",
          ".sym-forest",
          ".sym-wheel-link.is-active",
        ];
        return selectors.map((selector) => {
          const el = document.querySelector(selector)!;
          const r = el.getBoundingClientRect(),
            s = getComputedStyle(el);
          return {
            selector,
            x: r.x,
            y: r.y,
            width: r.width,
            height: r.height,
            background: s.backgroundImage,
            border: s.border,
            shadow: s.boxShadow,
          };
        });
      });
    const baseline = await geometry();
    const icons = await page
      .locator(".sym-wheel-link > svg")
      .evaluateAll((elements) => elements.map((el) => el.innerHTML));
    for (const path of routes) {
      await page.locator(`.sym-wheel-link[data-section="${path}"]`).click();
      await expect(page.locator(".sym-wheel-link.is-active")).toHaveAttribute(
        "data-section",
        path,
      );
      await expect(page.locator(".sym-wheel-link.is-active")).toHaveAttribute(
        "data-slot",
        "4",
      );
      expect(await geometry()).toEqual(baseline);
      expect(
        await page
          .locator(".sym-wheel-link.is-active .sym-wheel-label")
          .evaluate(
            (el) =>
              el.scrollWidth <= el.clientWidth + 1 &&
              el.scrollHeight <= el.clientHeight + 1,
          ),
      ).toBe(true);
      expect(
        await page
          .locator(".sym-wheel-link > svg")
          .evaluateAll((elements) => elements.map((el) => el.innerHTML)),
      ).toEqual(icons);
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
      await expect(page.locator(".sym-settings")).toBeInViewport();
      if (viewport.width > 950) {
        const link = page.locator(".sym-wheel-link.is-active");
        await expect(link).toHaveCSS("height", "62px");
        await expect(link).toHaveCSS("width", "186px");
      }
    }
    await page.evaluate(() =>
      scrollTo(0, document.documentElement.scrollHeight),
    );
    expect(await geometry()).toEqual(baseline);
  });
}

test("une animation interrompue repart de sa position courante sans clignotement", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1600, height: 900 });
  await page.clock.install();
  await page.clock.pauseAt(new Date());
  await page.goto("/");
  const wheel = page.locator(".sym-wheel");
  await page
    .locator('.sym-wheel-link[data-section="/videos"]')
    .dispatchEvent("click");
  await expect(wheel).toHaveAttribute("data-motion", "rotating");
  await page.clock.runFor(200);
  const centers = () =>
    page.locator(".sym-wheel-link").evaluateAll((elements) =>
      elements.map((el) => {
        const rect = el.getBoundingClientRect();
        return {
          x: rect.x + rect.width / 2,
          y: rect.y + rect.height / 2,
          opacity: getComputedStyle(el).opacity,
        };
      }),
    );
  const before = await centers();
  await page
    .locator('.sym-wheel-link[data-section="/documents"]')
    .dispatchEvent("click");
  await expect(page.locator(".sym-wheel-link.is-active")).toHaveAttribute(
    "data-section",
    "/documents",
  );
  const after = await centers();
  after.forEach((point, index) => {
    expect(Math.abs(point.x - before[index].x)).toBeLessThan(0.2);
    expect(Math.abs(point.y - before[index].y)).toBeLessThan(0.2);
    expect(point.opacity).toBe(before[index].opacity);
  });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await expect(wheel).toHaveAttribute("data-motion", "idle");
  const settled = await centers();
  await page.clock.runFor(1000);
  expect(await centers()).toEqual(settled);
});

test("les contrôles partagés conservent un focus clavier visible", async ({
  page,
}) => {
  await page.goto("/documents");
  const select = page.getByLabel("Espèce du corpus", { exact: true });
  await select.focus();
  await page.keyboard.press("ArrowDown");
  await expect(select).toHaveCSS("outline-style", "solid");
  await expect(select).toHaveCSS("outline-width", "2px");
});
