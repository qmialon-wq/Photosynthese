import { test, expect } from "@playwright/test";
import { guideFixture } from "./client-guide-fixture";
import { mkdir } from "node:fs/promises";
import { join } from "node:path";
import AxeBuilder from "@axe-core/playwright";

test("captures des écrans réels pour le guide client", async ({ page }) => {
  test.skip(
    !process.env.CLIENT_GUIDE_CAPTURE_DIR,
    "Génération explicite des captures du guide",
  );
  await page.setViewportSize({ width: 1600, height: 900 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await guideFixture(page);
  const directory = process.env.CLIENT_GUIDE_CAPTURE_DIR!;
  await mkdir(directory, { recursive: true });
  for (const [name, path] of [
    ["home", "/"],
    ["videos", "/videos"],
    ["analysis", "/analyses?video=premiere"],
    ["review", "/review"],
    ["projects", "/videos"],
    ["documents", "/documents"],
  ]) {
    await page.goto(path);
    await expect(page.locator("h1")).toBeVisible();
    if (name === "analysis")
      await page.getByLabel("Recevoir mon dossier biodiversité").uncheck();
    if (name === "projects") {
      await page
        .getByLabel("Sélectionner premiere-capture.mp4", { exact: true })
        .check();
      await page
        .getByLabel("Sélectionner seconde-capture.mp4", { exact: true })
        .check();
    }
    if (name === "videos" || name === "projects")
      await expect(
        page.locator(".sv-real-thumbnail img").first(),
      ).toBeVisible();
    if (name === "documents")
      await expect(page.locator(".sd-document-card")).toHaveCount(1);
    if (name === "review")
      expect(
        (
          await new AxeBuilder({ page })
            .include(".crop-grid")
            .withRules(["color-contrast"])
            .analyze()
        ).violations,
      ).toEqual([]);
    await page.evaluate(async () => {
      await document.fonts.ready;
      await Promise.all(
        [...document.images].map((image) => image.decode().catch(() => {})),
      );
    });
    if (name === "analysis") {
      await page
        .locator(".analysis-layout > section")
        .last()
        .screenshot({ path: join(directory, `${name}.png`) });
      continue;
    }
    const main = await page.locator(".sym-main").boundingBox();
    await page.screenshot({
      path: join(directory, `${name}.png`),
      ...(name === "home"
        ? {}
        : {
            clip: {
              x: main!.x,
              y: main!.y,
              width: main!.width,
              height: Math.min(760, 900 - main!.y),
            },
          }),
    });
  }
});
