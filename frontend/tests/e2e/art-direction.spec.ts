import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { readFileSync } from "node:fs";
const manifest = JSON.parse(
  readFileSync(
    new URL("../../public/experience-art/manifest.json", import.meta.url),
    "utf8",
  ),
);

test("eight real scene previews, explicit provenance and missing resources, no API or remote images", async ({
  page,
}) => {
  const errors: string[] = [],
    external: string[] = [],
    api: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (!["localhost", "127.0.0.1"].includes(url.hostname))
      external.push(request.url());
    if (url.pathname.startsWith("/api/")) api.push(request.url());
  });
  await page.setViewportSize({ width: 1600, height: 1000 });
  await page.goto("/experience-art/index.html");
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "L’atelier du vivant.",
  );
  await expect(page.locator("#asset-count")).toHaveText(
    "16 produits · 41 absents déclarés",
  );
  await expect(page.locator("#scene-rail button")).toHaveCount(8);
  for (const scene of manifest.scenes) {
    await page
      .getByRole("button", {
        name: `0${scene.index}. ${scene.name}`,
        exact: true,
      })
      .click();
    await expect(page.locator("#scene-image")).toHaveAttribute(
      "src",
      `./${scene.id}/primary-v1.png`,
    );
    await page
      .locator("#scene-image")
      .evaluate((element: HTMLImageElement) => element.decode());
    await expect(page.locator("#scene-title")).toHaveText(scene.name);
    await expect(page.locator("#disclosure")).toContainText(
      scene.id === "coast"
        ? "Évocation générée d’Étretat"
        : "Image générée par IA",
    );
    await expect(
      page.locator('#inventory li[data-status="missing"]'),
    ).toHaveCount(scene.id === "meadow" ? 6 : 5);
    await page
      .locator("#viewer")
      .screenshot({
        path: `../output/symbiose/art-direction/scenes/0${scene.index}-${scene.id}.png`,
      });
    await page
      .getByRole("button", { name: "Premier plan · alpha", exact: true })
      .click();
    await expect(page.locator("#viewer")).toHaveAttribute(
      "data-representation",
      "foreground",
    );
    await expect(page.locator("#scene-image")).toHaveAttribute(
      "src",
      `./${scene.id}/foreground-v1.png`,
    );
    await page
      .locator("#scene-image")
      .evaluate((element: HTMLImageElement) => element.decode());
    await expect(page.locator("#image-failure")).not.toBeVisible();
    if (scene.id === "coast")
      await page
        .locator("#viewer")
        .screenshot({
          path: "../output/symbiose/art-direction/alpha-coast.png",
        });
  }
  await page.getByRole("button", { name: "01. Forêt", exact: true }).click();
  expect(
    (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze())
      .violations,
  ).toEqual([]);
  await page
    .getByText("Comparer les huit compositions", { exact: true })
    .click();
  await expect(page.locator("#contact-sheet figure")).toHaveCount(8);
  for (const ratio of await page
    .locator("#contact-sheet img")
    .evaluateAll((images) =>
      images.map((image) => {
        const box = image.getBoundingClientRect();
        return box.width / box.height;
      }),
    ))
    expect(ratio).toBeCloseTo(16 / 9, 1);
  await page
    .locator(".comparison")
    .screenshot({ path: "../output/symbiose/art-direction/contact-sheet.png" });
  await page.screenshot({
    path: "../output/symbiose/art-direction/review-desktop.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
  expect(external).toEqual([]);
  expect(api).toEqual([]);
});

test("keyboard navigation, mobile review and official product logo on the landing", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/experience-art/index.html");
  const first = page.getByRole("button", { name: "01. Forêt", exact: true });
  await first.focus();
  await page.keyboard.press("ArrowRight");
  await expect(page.locator("#scene-title")).toHaveText("Ciel et nuages");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page
    .getByRole("button", { name: "07. Littoral — Étretat", exact: true })
    .click();
  await page.evaluate(() => scrollTo(0, 0));
  await page.screenshot({
    path: "../output/symbiose/art-direction/review-mobile.png",
  });
  expect(
    (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze())
      .violations,
  ).toEqual([]);
  await page.route("**/api/**", (route) =>
    route.fulfill({ status: 401, json: { detail: "Connexion requise" } }),
  );
  await page.goto("/");
  await expect(page.locator(".sx-brand img")).toHaveJSProperty(
    "naturalWidth",
    3634,
  );
  await expect(page.locator(".sx-brand svg")).toHaveCount(0);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "Le projet", exact: true }).click();
  await page.getByRole("link", { name: "Voir les huit atmosphères" }).click();
  await expect(page).toHaveURL(/\/experience-art\/index\.html$/);
  await expect(page.locator("#asset-count")).toHaveText(
    "16 produits · 41 absents déclarés",
  );
});

test("manifest load failure is visible and the retry actually reloads it", async ({
  page,
}) => {
  let attempts = 0;
  await page.route("**/experience-art/manifest.json", (route) =>
    ++attempts === 1
      ? route.fulfill({ status: 503, body: "Unavailable" })
      : route.continue(),
  );
  await page.goto("/experience-art/index.html");
  await expect(page.locator("#load-error")).toBeVisible();
  await page.getByRole("button", { name: "Réessayer", exact: true }).click();
  await expect(page.locator("#scene-title")).toHaveText("Forêt");
  await expect(page.locator("#load-error")).not.toBeVisible();
});
