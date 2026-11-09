import { test, expect } from "@playwright/test";
const session = {
  user: {
    id: "client-test",
    email: "camille@example.test",
    display_name: "Camille",
    role: "client",
    created_at: "2026-11-08T10:00:00Z",
    deleted_at: null,
  },
  csrf_token: "csrf-session-test",
};

test("déconnexion depuis le profil après un rechargement de page", async ({
  page,
}) => {
  let sessionReads = 0,
    logouts = 0;
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/auth/me") {
      sessionReads++;
      return route.fulfill({ json: session });
    }
    if (path === "/api/auth/logout") {
      expect(route.request().method()).toBe("POST");
      expect(route.request().headers()["x-csrf-token"]).toBe(
        session.csrf_token,
      );
      logouts++;
      return route.fulfill({ status: 204 });
    }
    if (path === "/api/auth/status")
      return route.fulfill({ json: { setup_required: false } });
    return route.fulfill({ json: [] });
  });
  await page.goto("/documents");
  await page.reload();
  await page.getByRole("button", { name: "Mon profil", exact: true }).click();
  await page
    .getByRole("button", { name: "Se déconnecter", exact: true })
    .click();
  await expect(page).toHaveURL(/\/connexion$/);
  await expect(
    page.getByRole("heading", { name: "Connexion", exact: true }),
  ).toBeVisible();
  expect(sessionReads).toBe(1);
  expect(logouts).toBe(1);
});

test("une erreur de déconnexion garde la session et permet de réessayer", async ({
  page,
}) => {
  let attempts = 0,
    sessionReads = 0;
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/auth/me") {
      sessionReads++;
      return route.fulfill({ json: session });
    }
    if (path === "/api/auth/logout") {
      expect(route.request().headers()["x-csrf-token"]).toBe(
        session.csrf_token,
      );
      return ++attempts === 1
        ? route.fulfill({
            status: 503,
            json: { detail: "Déconnexion temporairement indisponible" },
          })
        : route.fulfill({ status: 204 });
    }
    return route.fulfill({ json: { setup_required: false } });
  });
  await page.goto("/videos");
  await page.getByRole("button", { name: "Mon profil", exact: true }).click();
  await page
    .getByRole("button", { name: "Se déconnecter", exact: true })
    .click();
  await expect(page.getByRole("alert")).toHaveText(
    "Déconnexion temporairement indisponible",
  );
  await expect(page).toHaveURL(/\/videos$/);
  await expect(page.getByText("Camille", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Se déconnecter", exact: true })
    .click();
  await expect(page).toHaveURL(/\/connexion$/);
  expect(attempts).toBe(2);
  expect(sessionReads).toBe(1);
});

test("une session absente retourne à la connexion", async ({ page }) => {
  let logouts = 0;
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/auth/me")
      return route.fulfill({
        status: 401,
        json: { detail: "Connexion requise" },
      });
    if (path === "/api/auth/logout") logouts++;
    return route.fulfill({ json: { setup_required: false } });
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Mon profil", exact: true }).click();
  await page
    .getByRole("button", { name: "Se déconnecter", exact: true })
    .click();
  await expect(page).toHaveURL(/\/connexion$/);
  expect(logouts).toBe(0);
});
