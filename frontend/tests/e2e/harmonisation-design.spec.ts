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
  await page.goto("/");
  // Charger les écrans avant de mesurer la continuité des animations.
  for (const path of routes.slice(1)) {
    await page.locator(`.sym-wheel-link[data-section="${path}"]`).click();
    await expect(page.locator(".sym-wheel-link.is-active")).toHaveAttribute(
      "data-section",
      path,
    );
  }
  await page.evaluate(async () => {
    await Promise.all(
      document.getAnimations().map((a) => a.finished.catch(() => {})),
    );
  });
  await page.locator('.sym-wheel-link[data-section="/"]').click();
  const before = await page.locator(".sym-wheel-link").evaluateAll((elements) =>
    elements.map((el) => {
      const animation = el
        .getAnimations()
        .find(
          (a) =>
            (a.effect as KeyframeEffect).getKeyframes()[0].left !== undefined,
        )!;
      animation.pause();
      animation.currentTime = 240;
      const style = getComputedStyle(el);
      return { left: parseFloat(style.left), top: parseFloat(style.top) };
    }),
  );
  await page
    .locator('.sym-wheel-link[data-section="/analyses"]')
    .dispatchEvent("click");
  await expect(page.locator(".sym-wheel-link.is-active")).toHaveAttribute(
    "data-section",
    "/analyses",
  );
  const starts = await page.locator(".sym-wheel-link").evaluateAll((elements) =>
    elements.map((el) => {
      const animation = el
        .getAnimations()
        .find(
          (a) =>
            (a.effect as KeyframeEffect).getKeyframes()[0].left !== undefined,
        )!;
      const first = (animation.effect as KeyframeEffect).getKeyframes()[0];
      const parent = el.parentElement!.getBoundingClientRect();
      return {
        left: (parseFloat(String(first.left)) * parent.width) / 100,
        top: (parseFloat(String(first.top)) * parent.height) / 100,
        opacity: Number(first.opacity),
      };
    }),
  );
  starts.forEach((point, index) => {
    expect(Math.abs(point.left - before[index].left)).toBeLessThan(0.2);
    expect(Math.abs(point.top - before[index].top)).toBeLessThan(0.2);
    expect(point.opacity).toBe(1);
  });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await expect
    .poll(() =>
      page
        .locator(".sym-wheel-link")
        .evaluateAll(
          (elements) => elements.flatMap((el) => el.getAnimations()).length,
        ),
    )
    .toBe(0);
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
