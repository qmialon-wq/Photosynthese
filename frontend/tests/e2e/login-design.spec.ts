import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

async function unauthenticated(page: Page) {
  await page.route("**/api/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/auth/me")
      return route.fulfill({
        status: 401,
        json: { detail: "Connexion requise" },
      });
    if (path === "/api/auth/status")
      return route.fulfill({ json: { setup_required: false } });
    return route.fulfill({ json: [] });
  });
}

for (const viewport of [
  { width: 1672, height: 941 },
  { width: 390, height: 844 },
]) {
  test(`connexion lisible et accessible à ${viewport.width}px`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize(viewport);
    await unauthenticated(page);
    await page.goto("/connexion");
    await expect(
      page.getByRole("heading", { name: "Se connecter" }),
    ).toBeVisible();
    const logo = page.getByRole("img", { name: "Symbiose", exact: true });
    await expect(logo).toBeVisible();
    expect(
      await logo.evaluate(
        (img: HTMLImageElement) => img.complete && img.naturalWidth > 0,
      ),
    ).toBe(true);
    await expect(
      page.getByRole("button", { name: "Se connecter", exact: true }),
    ).toBeInViewport();
    await expect(
      page.getByRole("link", { name: "Créer un compte", exact: true }),
    ).toBeInViewport();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    const scan = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(scan.violations).toEqual([]);
    await page.screenshot({
      path: testInfo.outputPath("connexion.png"),
      fullPage: true,
    });
  });
}

test("affichage du mot de passe, aide et nouvelle tentative après une erreur", async ({
  page,
}) => {
  await unauthenticated(page);
  let attempts = 0;
  await page.route("**/api/auth/login", async (route) => {
    expect(route.request().postDataJSON()).toEqual({
      email: "camille@example.test",
      password: "phrase-de-passe-test",
    });
    if (++attempts === 1)
      return route.fulfill({
        status: 401,
        json: { detail: "Identifiants incorrects" },
      });
    return route.fulfill({
      json: {
        user: {
          id: "client-test",
          email: "camille@example.test",
          display_name: "Camille",
          role: "client",
          created_at: "2026-11-05T10:00:00Z",
          deleted_at: null,
        },
        csrf_token: "test-csrf",
      },
    });
  });
  await page.goto("/connexion");
  await page.getByLabel("Adresse e-mail").fill("camille@example.test");
  const password = page.getByLabel("Mot de passe", { exact: true });
  await password.fill("phrase-de-passe-test");
  await expect(password).toHaveAttribute("type", "password");
  await page
    .getByRole("button", { name: "Afficher le mot de passe", exact: true })
    .click();
  await expect(password).toHaveAttribute("type", "text");
  await page
    .getByRole("button", { name: "Masquer le mot de passe", exact: true })
    .click();
  await expect(password).toHaveAttribute("type", "password");
  await page
    .getByRole("button", { name: "Mot de passe oublié ?", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText(
    "Demandez un lien de réinitialisation à un administrateur.",
  );
  await page.getByRole("button", { name: "Se connecter", exact: true }).click();
  await expect(page.getByRole("alert")).toHaveText("Identifiants incorrects");
  await expect(password).toHaveValue("phrase-de-passe-test");
  await page.getByRole("button", { name: "Se connecter", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Vos observations, simplement." }),
  ).toBeVisible();
});
