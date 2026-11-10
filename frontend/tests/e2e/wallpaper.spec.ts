import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

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
const session = {
  user: {
    id: "wallpaper-admin",
    display_name: "Camille",
    email: "camille@example.test",
    role: "admin",
    created_at: "2026-11-01",
    deleted_at: null,
  },
  csrf_token: "test-csrf",
};
async function fixture(page: Page) {
  await page.route("**/api/**", (route) =>
    route.fulfill({
      json: route.request().url().endsWith("/auth/me") ? session : [],
    }),
  );
}
async function settings(page: Page) {
  await page.getByRole("button", { name: "Paramètres", exact: true }).click();
  await page
    .getByRole("button", { name: "Paramètres d’affichage", exact: true })
    .click();
  await expect(
    page.getByRole("combobox", { name: "Source de données" }),
  ).toBeFocused();
}
async function chosen(page: Page, id: string) {
  await expect(page.locator(".sym-forest")).toHaveAttribute(
    "data-wallpaper",
    id,
  );
  await expect(page.locator(".sym-wallpaper-incoming")).toHaveCount(0);
}
async function close(page: Page) {
  await page
    .locator(".sym-action-panel")
    .getByRole("button", { name: "Fermer", exact: true })
    .click();
}
test.use({ viewport: { width: 1600, height: 900 } });

test("huit photographies, galerie, contraste et captures sans changement de géométrie", async ({
  page,
}, info) => {
  test.setTimeout(120000);
  await fixture(page);
  const photographs = new Set<string>();
  page.on("request", (r) => {
    if (
      r.resourceType() === "image" &&
      /backgrounds\/[^/]+\.webp/.test(r.url()) &&
      !r.url().includes("-thumb")
    )
      photographs.add(r.url());
  });
  await page.goto("/");
  await chosen(page, "forest");
  const wheel = await page.locator(".sym-wheel").boundingBox();
  expect(photographs.size).toBe(1);
  await expect(page.locator(".sym-header-actions button")).toHaveCount(2);
  await expect(page.locator("header select")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Rechercher", exact: true }),
  ).toHaveCount(0);
  for (const [id, name] of themes) {
    await settings(page);
    await expect(page.getByRole("radio")).toHaveCount(8);
    await page.getByRole("radio", { name, exact: true }).check();
    await chosen(page, id);
    await expect(page.getByRole("radio", { name, exact: true })).toBeChecked();
    await expect(page.locator(".sym-wallpaper-card.is-selected")).toHaveCount(
      1,
    );
    const violations = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(
      violations.violations.map((v) => ({
        id: v.id,
        targets: v.nodes.map((n) => n.target),
      })),
    ).toEqual([]);
    await page.screenshot({
      path: info.outputPath(`${id}-settings-1600x900.png`),
    });
    await close(page);
    expect(await page.locator(".sym-wheel").boundingBox()).toEqual(wheel);
    await page.screenshot({ path: info.outputPath(`${id}-1600x900.png`) });
  }
  expect(photographs.size).toBe(8);
  await settings(page);
  await page.getByLabel("Réduire les animations").check();
  await page
    .getByRole("button", { name: "Restaurer le fond par défaut" })
    .click();
  await chosen(page, "forest");
  await expect(page.getByLabel("Réduire les animations")).toBeChecked();
  await expect(
    page.getByRole("combobox", { name: "Source de données" }),
  ).toHaveValue("demo");
});

test("persistance, six rubriques, profil, administration et mode global indépendant", async ({
  page,
}, info) => {
  await fixture(page);
  await page.goto("/");
  await settings(page);
  await page.getByRole("radio", { name: "Littoral", exact: true }).check();
  await chosen(page, "coast");
  await close(page);
  for (const path of [
    "/videos",
    "/parcelles",
    "/analyses",
    "/review",
    "/documents",
    "/",
  ]) {
    await page.locator(`.sym-wheel-link[data-section="${path}"]`).click();
    await expect(page.locator(".sym-wheel")).toHaveAttribute(
      "data-motion",
      "idle",
    );
    await chosen(page, "coast");
  }
  await page.reload();
  await chosen(page, "coast");
  await settings(page);
  await expect(
    page.getByRole("radio", { name: "Littoral", exact: true }),
  ).toBeChecked();
  await page
    .getByRole("combobox", { name: "Source de données" })
    .selectOption("real");
  await chosen(page, "coast");
  await page
    .getByRole("combobox", { name: "Source de données" })
    .selectOption("demo");
  await close(page);
  await page
    .getByRole("button", { name: "Notifications", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Notifications", exact: true }),
  ).toBeVisible();
  await close(page);
  await page.getByRole("button", { name: "Mon profil", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Votre espace Symbiose" }),
  ).toBeVisible();
  await close(page);
  await page.getByRole("button", { name: "Paramètres", exact: true }).click();
  await page.getByRole("link", { name: "Administration", exact: true }).click();
  await chosen(page, "coast");
  await expect(page.locator(".adm-shell")).toBeVisible();
  await expect(page.locator("header select")).toHaveCount(0);
  await page.screenshot({ path: info.outputPath("admin-coast-1600x900.png") });
  await settings(page);
  await expect(
    page.getByRole("radio", { name: "Littoral", exact: true }),
  ).toBeChecked();
  await page.getByRole("radio", { name: "Rivière", exact: true }).check();
  await chosen(page, "river");
  await close(page);
  await page
    .locator("header")
    .getByRole("link", { name: "Mon profil", exact: true })
    .click();
  await expect(page).toHaveURL(/\/profil$/);
  await chosen(page, "river");
  await page.screenshot({ path: info.outputPath("profil-river-1600x900.png") });
  const profileScan = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(
    profileScan.violations.map((v) => ({
      id: v.id,
      targets: v.nodes.map((n) => n.target),
    })),
  ).toEqual([]);
  await settings(page);
  await expect(
    page.getByRole("combobox", { name: "Source de données" }),
  ).toHaveValue("demo");
  await expect(
    page.getByRole("radio", { name: "Rivière", exact: true }),
  ).toBeChecked();
});

test("échec de photo : choix précédent conservé et erreur discrète", async ({
  page,
}) => {
  await fixture(page);
  await page.route("**/backgrounds/sky.webp*", (route) =>
    route.request().resourceType() === "image"
      ? route.abort()
      : route.continue(),
  );
  await page.goto("/");
  await settings(page);
  await page
    .getByRole("radio", { name: "Ciel et nuages", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText(
    "Le fond précédent est conservé",
  );
  await chosen(page, "forest");
  await expect(
    page.getByRole("radio", { name: "Forêt", exact: true }),
  ).toBeChecked();
  expect(
    await page.evaluate(() => localStorage.getItem("symbiose:wallpaper:v1")),
  ).toBeNull();
});

test("clavier, fondu de deux couches, sélections rapides et réduction des animations", async ({
  page,
}) => {
  await fixture(page);
  await page.goto("/");
  await settings(page);
  await page.getByRole("radio", { name: "Forêt", exact: true }).focus();
  await page.keyboard.press("ArrowRight");
  await expect(
    page.getByRole("radio", { name: "Ciel et nuages", exact: true }),
  ).toBeFocused();
  await expect(page.locator(".sym-wallpaper-incoming")).toHaveCSS(
    "transition-duration",
    "0.65s",
  );
  const count = await page.locator(".sym-wallpaper-layer").count();
  expect(count).toBe(2);
  await page.getByRole("radio", { name: "Rivière", exact: true }).click();
  await page.getByRole("radio", { name: "Littoral", exact: true }).click();
  await chosen(page, "coast");
  await page.getByLabel("Réduire les animations").check();
  await page
    .getByRole("radio", { name: "Forêt nocturne", exact: true })
    .check();
  await chosen(page, "night-forest");
  await page.reload();
  await settings(page);
  await expect(page.getByLabel("Réduire les animations")).toBeChecked();
  await page.getByLabel("Réduire les animations").uncheck();
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.getByRole("radio", { name: "Zones humides", exact: true }).check();
  await chosen(page, "wetland");
});

for (const viewport of [
  { width: 800, height: 600 },
  { width: 390, height: 844 },
  { width: 320, height: 568 },
]) {
  test(`panneau accessible et défilant à ${viewport.width} × ${viewport.height}`, async ({
    page,
  }, info) => {
    await fixture(page);
    await page.setViewportSize(viewport);
    await page.goto("/");
    await settings(page);
    const panel = page.locator(".sym-display-settings-panel");
    const rect = await panel.boundingBox();
    expect(rect!.x).toBeGreaterThanOrEqual(0);
    expect(rect!.y).toBeGreaterThanOrEqual(0);
    expect(rect!.x + rect!.width).toBeLessThanOrEqual(viewport.width);
    expect(rect!.y + rect!.height).toBeLessThanOrEqual(viewport.height);
    await page
      .getByRole("radio", { name: "Forêt nocturne", exact: true })
      .check();
    await chosen(page, "night-forest");
    await page
      .getByRole("button", { name: "Restaurer le fond par défaut" })
      .click();
    await chosen(page, "forest");
    await expect(
      panel.getByRole("button", { name: "Fermer", exact: true }),
    ).toBeInViewport();
    await page.screenshot({
      path: info.outputPath(`settings-${viewport.width}.png`),
    });
    await page.keyboard.press("Escape");
    await expect(panel).toHaveCount(0);
    await expect(
      page.getByRole("button", { name: "Paramètres", exact: true }),
    ).toBeFocused();
    await page.goto("/admin");
    await page
      .getByRole("button", { name: "Navigation administrative", exact: true })
      .click();
    await settings(page);
    await expect(
      page.getByRole("button", {
        name: "Navigation administrative",
        exact: true,
      }),
    ).toHaveAttribute("aria-expanded", "false");
    await expect(
      page.getByRole("radio", { name: "Forêt nocturne", exact: true }),
    ).toBeAttached();
    const adminRect = await page
      .locator(".sym-display-settings-panel")
      .boundingBox();
    expect(adminRect!.y).toBeGreaterThanOrEqual(0);
    await close(page);
  });
}
