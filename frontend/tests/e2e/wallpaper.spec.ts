import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { mockApi } from "./mock-api";

const themes = [
  ["forest", "Forêt"],
  ["sky", "Ciel et nuages"],
  ["river", "Rivière"],
  ["underwater", "Monde sous-marin"],
  ["wetland", "Zones humides"],
  ["meadow", "Prairie et bocage"],
  ["coast", "Littoral"],
  ["night-forest", "Forêt nocturne"],
] as const;
async function settings(page: Page) {
  await page.getByRole("button", { name: "Paramètres", exact: true }).click();
  await page
    .getByRole("button", { name: "Paramètres d’affichage", exact: true })
    .click();
}
async function chosen(page: Page, id: string) {
  await expect(page.locator(".sym-forest")).toHaveAttribute(
    "data-wallpaper",
    id,
  );
  await expect(page.locator(".sym-wallpaper-incoming")).toHaveCount(0);
}
test.beforeEach(async ({ page }) => {
  await mockApi(page, (route) => route.fulfill({ json: [] }));
});

test("les huit fonds restent accessibles sans sélecteur de démonstration", async ({
  page,
}) => {
  test.setTimeout(60000);
  await page.goto("/videos");
  await settings(page);
  await expect(page.getByLabel("Source de données")).toHaveCount(0);
  for (const [id, name] of themes) {
    await page.getByRole("radio", { name, exact: true }).check();
    await chosen(page, id);
    await expect(page.getByRole("radio", { name, exact: true })).toBeChecked();
  }
  expect(
    (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze())
      .violations,
  ).toEqual([]);
  await page.getByLabel("Réduire les animations").check();
  await page
    .getByRole("button", { name: "Restaurer le fond par défaut" })
    .click();
  await chosen(page, "forest");
  await expect(page.getByLabel("Réduire les animations")).toBeChecked();
});

test("le choix persiste après rechargement et entre les pages de travail", async ({
  page,
}) => {
  await page.goto("/videos");
  await settings(page);
  await page.getByRole("radio", { name: "Littoral", exact: true }).check();
  await chosen(page, "coast");
  await page.reload();
  await chosen(page, "coast");
  for (const path of [
    "/analyses",
    "/review",
    "/documents",
    "/parcelles",
    "/profil",
    "/admin/models",
  ]) {
    await page.goto(path);
    await chosen(page, "coast");
  }
});

test("un échec de chargement conserve le fond précédent", async ({ page }) => {
  await page.route("**/backgrounds/sky.webp*", (route) =>
    route.request().resourceType() === "image"
      ? route.abort()
      : route.continue(),
  );
  await page.goto("/videos");
  await settings(page);
  await page
    .getByRole("radio", { name: "Ciel et nuages", exact: true })
    .check();
  await expect(page.locator(".sym-wallpaper-status")).toContainText(
    /n’a pas pu être chargé/,
  );
  await chosen(page, "forest");
});

for (const width of [390, 768]) {
  test(`les réglages restent utilisables à ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 844 });
    await page.goto("/videos");
    await settings(page);
    await expect(page.getByLabel("Réduire les animations")).toBeFocused();
    await page.getByRole("radio", { name: "Rivière", exact: true }).check();
    await chosen(page, "river");
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  });
}
