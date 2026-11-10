import { test, expect, type Page } from "@playwright/test";

const paths = [
  "/",
  "/videos",
  "/parcelles",
  "/analyses",
  "/review",
  "/documents",
];
const slots = [
  [230, 187],
  [171, 263],
  [133, 349],
  [161, 449],
  [133, 545],
  [171, 628],
];
const wheel = (page: Page) => page.locator(".sym-wheel");
const link = (page: Page, path: string) =>
  page.locator(`.sym-wheel-link[data-section="${path}"]`);

async function verifyRest(page: Page, active: number) {
  await expect(
    page.locator('.sym-wheel-link[aria-current="page"]'),
  ).toHaveCount(1);
  await expect(link(page, paths[active])).toHaveAttribute(
    "aria-current",
    "page",
  );
  await expect(wheel(page)).toHaveAttribute("data-motion", "idle");
  const poses = await page.locator(".sym-wheel-link").evaluateAll((elements) =>
    elements.map((el) => {
      const rect = el.getBoundingClientRect();
      const parent = el.parentElement!.getBoundingClientRect();
      return {
        x: ((rect.x + rect.width / 2 - parent.x) / parent.width) * 300,
        y: ((rect.y + rect.height / 2 - parent.y) / parent.height) * 852,
        opacity: getComputedStyle(el).opacity,
        icon: getComputedStyle(el.querySelector("svg")!).transform,
        engagement: Number(
          (el as HTMLElement).style.getPropertyValue("--wheel-engagement"),
        ),
      };
    }),
  );
  poses.forEach((pose, index) => {
    const slot = (index - active + 9) % 6;
    expect(pose.x).toBeCloseTo(slots[slot][0], 1);
    expect(pose.y).toBeCloseTo(slots[slot][1], 1);
    expect(pose.opacity).toBe("1");
    expect(pose.icon).toBe("none");
    expect(pose.engagement).toBe(index === active ? 1 : 0);
  });
  expect(
    await wheel(page).evaluate((el) =>
      (el as HTMLElement).style.getPropertyValue("--wheel-lock"),
    ),
  ).toBe("0");
}

test.use({
  viewport: { width: 1600, height: 900 },
  video: { mode: "on", size: { width: 1600, height: 900 } },
});

test("tous les crans, les deux sens et les raccourcis cycliques retrouvent leurs positions", async ({
  page,
}) => {
  await page.goto("/");
  const arc = await page.locator(".sym-wheel-arc path").getAttribute("d");
  const marker = await page.locator(".sym-wheel-detent").boundingBox();
  for (const active of [1, 2, 3, 4, 5, 0, 5, 4, 3, 2, 1, 0, 3, 0, 2, 5]) {
    await link(page, paths[active]).click();
    await expect(page).toHaveURL(new RegExp(`${paths[active]}$`));
    await verifyRest(page, active);
    expect(await page.locator(".sym-wheel-arc path").getAttribute("d")).toBe(
      arc,
    );
    expect(await page.locator(".sym-wheel-detent").boundingBox()).toEqual(
      marker,
    );
  }
});

test("les clics rapprochés, le clavier et le changement de préférence ne laissent aucun mouvement résiduel", async ({
  page,
}) => {
  await page.clock.install();
  await page.clock.pauseAt(new Date());
  await page.goto("/");
  for (const active of [1, 5, 3, 0, 4, 2]) {
    await link(page, paths[active]).dispatchEvent("click");
    await expect(link(page, paths[active])).toHaveAttribute(
      "aria-current",
      "page",
    );
    await page.clock.runFor(96);
  }
  await page.clock.runFor(1000);
  await verifyRest(page, 2);
  await link(page, paths[2]).focus();
  await page.keyboard.press("ArrowDown");
  await expect(link(page, paths[3])).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(wheel(page)).toHaveAttribute("data-motion", "rotating");
  await page.clock.runFor(200);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await verifyRest(page, 3);
  await page.clock.runFor(1500);
  await verifyRest(page, 3);
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.getByRole("button", { name: "Paramètres", exact: true }).click();
  await page.getByRole("button", { name: "Paramètres d’affichage" }).click();
  await page.getByLabel("Réduire les animations").check();
  await page.keyboard.press("Escape");
  await link(page, paths[5]).dispatchEvent("click");
  await verifyRest(page, 5);
});

test("le raccord aux extrémités est invisible et la pilule s'élargit pendant l'approche", async ({
  page,
}, testInfo) => {
  await page.clock.install();
  await page.clock.pauseAt(new Date());
  await page.goto("/");
  await link(page, "/videos").dispatchEvent("click");
  await expect(wheel(page)).toHaveAttribute("data-motion", "rotating");
  let previous: { y: number; opacity: number } | undefined;
  let hiddenWraps = 0;
  const widths: number[] = [];
  for (let elapsed = 0; elapsed < 800; elapsed += 16) {
    await page.clock.runFor(16);
    const pose = await link(page, "/analyses").evaluate((el) => {
      const rect = el.getBoundingClientRect();
      return {
        y: rect.y + rect.height / 2,
        opacity: Number(getComputedStyle(el).opacity),
      };
    });
    if (previous && Math.abs(pose.y - previous.y) > 200) {
      hiddenWraps++;
      expect(Math.max(pose.opacity, previous.opacity)).toBeLessThan(0.04);
    }
    previous = pose;
    widths.push((await link(page, "/videos").boundingBox())!.width);
    const textDoesNotOverlap = await link(page, "/videos").evaluate((el) => {
      const label = el.querySelector(".sym-wheel-label")!;
      const icon = el.querySelector("svg")!;
      return (
        Number(getComputedStyle(label).opacity) < 0.05 ||
        label.getBoundingClientRect().left >= icon.getBoundingClientRect().right
      );
    });
    expect(textDoesNotOverlap).toBe(true);
    if ([16, 128, 240, 352, 432, 528, 704].includes(elapsed + 16)) {
      await page.screenshot({
        path: testInfo.outputPath(`progression-${elapsed + 16}ms.png`),
      });
    }
  }
  expect(hiddenWraps).toBe(1);
  expect(widths.some((width) => width > 70 && width < 175)).toBe(true);
  await verifyRest(page, 1);
});

test("un redimensionnement pendant la rotation conserve le cran et les libellés mobiles", async ({
  page,
}, testInfo) => {
  await page.clock.install();
  await page.clock.pauseAt(new Date());
  await page.goto("/");
  await link(page, "/videos").dispatchEvent("click");
  await expect(wheel(page)).toHaveAttribute("data-motion", "rotating");
  await page.clock.runFor(200);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.clock.runFor(1000);
  await verifyRest(page, 1);
  await link(page, "/documents").dispatchEvent("click");
  await expect(link(page, "/documents")).toHaveAttribute(
    "aria-current",
    "page",
  );
  await page.clock.runFor(1000);
  await verifyRest(page, 5);
  const label = page.locator(".sym-wheel-link.is-active .sym-wheel-label");
  expect(
    await label.evaluate(
      (el) =>
        el.scrollWidth <= el.clientWidth + 1 &&
        el.scrollHeight <= el.clientHeight + 1,
    ),
  ).toBe(true);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({ path: testInfo.outputPath("documents-mobile.png") });
  await link(page, "/").dispatchEvent("click");
  await expect(link(page, "/")).toHaveAttribute("aria-current", "page");
  await page.clock.runFor(200);
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.clock.runFor(1000);
  await verifyRest(page, 0);
});

test.describe("capture animée", () => {
  test("démonstration de la molette à 1600 × 900", async ({
    page,
  }, testInfo) => {
    await page.goto("/");
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({
      path: testInfo.outputPath("accueil-1600x900.png"),
    });
    for (const active of [1, 2, 3, 4, 5, 0, 5, 0, 3]) {
      await link(page, paths[active]).click();
      await verifyRest(page, active);
      await page.mouse.move(500, 820);
    }
    for (const active of [1, 5, 4, 2]) {
      await link(page, paths[active]).dispatchEvent("click");
      await page.waitForTimeout(100);
    }
    await verifyRest(page, 2);
    await link(page, "/documents").click();
    await verifyRest(page, 5);
    await page.mouse.move(500, 820);
    await page.screenshot({
      path: testInfo.outputPath("documents-1600x900.png"),
    });
  });
});
