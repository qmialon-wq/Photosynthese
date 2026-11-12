import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { guideFixture } from "./client-guide-fixture";

const help = (page: import("@playwright/test").Page) =>
  page.getByRole("button", {
    name: "Aide — guide du compte client",
    exact: true,
  });

test("première visite : huit cartes, captures, mémorisation du compte et relance depuis Aide", async ({
  page,
}) => {
  const fixture = await guideFixture(page, null);
  await page.goto("/");
  const guide = page.getByRole("dialog", {
    name: "Bienvenue dans votre espace Symbiose",
    exact: true,
  });
  await expect(guide).toBeVisible();
  await expect(guide.getByRole("heading", { level: 2 })).toBeFocused();
  await expect(guide.getByRole("img")).toBeVisible();
  expect(
    (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze())
      .violations,
  ).toEqual([]);
  await page.screenshot({ path: "test-results/client-guide-desktop.png" });
  await guide.getByRole("button", { name: "Suivant", exact: true }).click();
  const dialog = page.locator("#client-guide");
  await expect(dialog.getByRole("heading", { level: 2 })).toHaveText(
    "Importez vos vidéos de terrain",
  );
  await dialog
    .getByRole("button", { name: "Agrandir la capture d’écran", exact: true })
    .click();
  await expect(
    dialog.getByRole("button", { name: "Revenir à la carte", exact: true }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(
    dialog.getByRole("button", { name: "Suivant", exact: true }),
  ).toBeVisible();
  await dialog.getByRole("button", { name: "Plus tard", exact: true }).click();
  await expect(dialog).not.toBeVisible();
  await expect.poll(fixture.marks).toBe(1);
  await page.reload();
  await expect(dialog).not.toBeVisible();
  await expect(help(page)).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Notifications", exact: true }),
  ).toHaveCount(0);
  await page.goto("/documents");
  await help(page).click();
  await expect(dialog.getByRole("heading", { level: 2 })).toHaveText(
    "Bienvenue dans votre espace Symbiose",
  );
  for (let index = 0; index < 7; index++)
    await dialog.getByRole("button", { name: "Suivant", exact: true }).click();
  await dialog
    .getByRole("button", { name: "Importer mes premières vidéos", exact: true })
    .click();
  await expect(page).toHaveURL(/\/videos$/);
  await expect(dialog).not.toBeVisible();
  expect(fixture.marks()).toBe(1);
});

test("le guide attend la fin de l'animation de connexion", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await guideFixture(page, null);
  await page.goto("/connexion");
  await page.getByLabel("Adresse e-mail").fill("camille@example.test");
  await page
    .getByLabel("Mot de passe", { exact: true })
    .fill("phrase-de-passe-test");
  await page.getByRole("button", { name: "Se connecter", exact: true }).click();
  await expect(page.locator('[data-testid="login-transition"]')).toBeVisible();
  await expect(page.locator("#client-guide")).not.toBeVisible();
  await page.getByRole("button", { name: "Passer", exact: true }).click();
  await expect(page.locator("#client-guide")).toBeVisible();
});

test("mobile et clavier : le guide reste lisible, contrôlable et refermable", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await guideFixture(page, null);
  await page.goto("/");
  const guide = page.locator("#client-guide");
  await expect(guide).toBeVisible();
  await expect(
    guide.getByRole("button", { name: "Suivant", exact: true }),
  ).toBeInViewport();
  await page.keyboard.press("ArrowRight");
  await expect(guide.getByRole("heading", { level: 2 })).toHaveText(
    "Importez vos vidéos de terrain",
  );
  await page.keyboard.press("ArrowLeft");
  await expect(guide.getByRole("heading", { level: 2 })).toHaveText(
    "Bienvenue dans votre espace Symbiose",
  );
  expect(await guide.evaluate((el) => el.scrollWidth <= el.clientWidth)).toBe(
    true,
  );
  expect(
    (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze())
      .violations,
  ).toEqual([]);
  await page.screenshot({ path: "test-results/client-guide-mobile.png" });
  await guide
    .getByRole("button", { name: "Agrandir la capture d’écran", exact: true })
    .click();
  await expect(
    guide.getByRole("region", {
      name: "Capture agrandie, faites défiler pour explorer les détails",
      exact: true,
    }),
  ).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(guide).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(guide).not.toBeVisible();
});

test("Aide est disponible sur les espaces client, administration, profil et pages publiques", async ({
  page,
}) => {
  await guideFixture(page);
  await page.route("**/api/auth/me", (route) =>
    route.fulfill({
      json: {
        user: {
          id: "guide-admin",
          role: "admin",
          display_name: "Admin",
          email: null,
          created_at: "2026-11-12",
          deleted_at: null,
          client_guide_seen_at: "2026-11-12",
        },
        csrf_token: "guide-csrf",
      },
    }),
  );
  for (const path of [
    "/videos",
    "/analyses",
    "/review",
    "/documents",
    "/parcelles",
    "/profil",
    "/admin/models",
    "/connexion",
  ]) {
    await page.goto(path);
    await expect(help(page)).toHaveCount(1);
    await help(page).click();
    await expect(page.locator("#client-guide")).toBeVisible();
    await page.keyboard.press("Escape");
  }
  await page.route("**/api/auth/me", (route) =>
    route.fulfill({ status: 401, json: { detail: "Connexion requise" } }),
  );
  await page.goto("/");
  await help(page).click();
  await expect(page.locator("#client-guide")).toBeVisible();
});
