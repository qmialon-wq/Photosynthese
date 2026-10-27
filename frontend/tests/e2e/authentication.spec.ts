import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const client = {
  id: "client-test",
  email: "client@example.test",
  display_name: "Camille",
  role: "client",
  created_at: "2026-10-27T10:00:00Z",
  deleted_at: null,
};

test("inscription client, profil, navigation protégée et déconnexion", async ({
  page,
}) => {
  let connected = false;
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname.replace("/api", "");
    if (path === "/auth/me")
      return route.fulfill(
        connected
          ? { json: { user: client, csrf_token: "test-csrf" } }
          : { status: 401, json: { detail: "Connexion requise" } },
      );
    if (path === "/auth/status")
      return route.fulfill({
        json: { setup_required: false, registration_open: true },
      });
    if (path === "/auth/register") {
      expect(route.request().postDataJSON()).toEqual({
        display_name: "Camille",
        email: "client@example.test",
        password: "phrase-de-passe-test",
      });
      connected = true;
      return route.fulfill({
        status: 201,
        json: { user: client, csrf_token: "test-csrf" },
      });
    }
    if (path === "/auth/logout") {
      expect(route.request().headers()["x-csrf-token"]).toBe("test-csrf");
      connected = false;
      return route.fulfill({ status: 204 });
    }
    return route.fulfill({ json: [] });
  });
  await page.goto("/admin/utilisateurs");
  await expect(page).toHaveURL(/\/connexion$/);
  await page.getByRole("link", { name: "S’inscrire" }).click();
  await page.getByLabel("Nom du profil").fill("Camille");
  await page.getByLabel("Adresse e-mail").fill("client@example.test");
  await page
    .getByLabel("Mot de passe", { exact: true })
    .fill("phrase-de-passe-test");
  await page
    .getByLabel("Confirmer le mot de passe")
    .fill("phrase-de-passe-test");
  expect(
    (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze())
      .violations,
  ).toEqual([]);
  await page.getByRole("button", { name: "Créer un compte client" }).click();
  await expect(
    page.getByRole("heading", { name: "Vos observations, simplement." }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Administration", exact: true }),
  ).toHaveCount(0);
  await page.goto("/admin/utilisateurs");
  await expect(page).toHaveURL(/\/$/);
  await page.getByRole("link", { name: "Mon profil" }).click();
  await expect(page.getByLabel("Nom du profil")).toHaveValue("Camille");
  await expect(
    page.getByRole("link", { name: "Télécharger mes données (JSON)" }),
  ).toHaveAttribute("href", "/api/auth/me/export");
  await page.getByRole("button", { name: "Se déconnecter" }).click();
  await expect(page).toHaveURL(/\/connexion$/);
});

test("initialisation et confirmation de suppression du profil", async ({
  page,
}) => {
  let connected = false;
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/auth/status"))
      return route.fulfill({
        json: { setup_required: !connected, registration_open: connected },
      });
    if (path.endsWith("/auth/setup")) {
      expect(route.request().postDataJSON().setup_token).toBe(
        "jeton-local-test",
      );
      connected = true;
      return route.fulfill({
        status: 201,
        json: { user: { ...client, role: "admin" }, csrf_token: "test-csrf" },
      });
    }
    if (path.endsWith("/auth/me") && route.request().method() === "DELETE") {
      expect(route.request().postDataJSON().confirmation).toBe("SUPPRIMER");
      connected = false;
      return route.fulfill({
        json: { erasure_request: "demande-test", status: "pending" },
      });
    }
    if (path.endsWith("/auth/me"))
      return route.fulfill(
        connected
          ? {
              json: {
                user: { ...client, role: "admin" },
                csrf_token: "test-csrf",
              },
            }
          : { status: 401, json: { detail: "Connexion requise" } },
      );
    return route.fulfill({ json: [] });
  });
  await page.goto("/connexion");
  await page
    .getByRole("link", { name: "Initialiser le premier administrateur" })
    .click();
  await page.getByLabel("Nom du profil").fill("Camille");
  await page.getByLabel("Adresse e-mail").fill("client@example.test");
  await page.getByLabel("Jeton d’initialisation").fill("jeton-local-test");
  await page
    .getByLabel("Mot de passe", { exact: true })
    .fill("phrase-de-passe-test");
  await page
    .getByLabel("Confirmer le mot de passe")
    .fill("phrase-de-passe-test");
  await page.getByRole("button", { name: "Premier administrateur" }).click();
  await page.getByRole("link", { name: "Mon profil" }).click();
  await page
    .getByLabel("Mot de passe actuel", { exact: true })
    .last()
    .fill("phrase-de-passe-test");
  await page.getByLabel("Saisir SUPPRIMER pour confirmer").fill("SUPPRIMER");
  await page
    .getByRole("button", {
      name: "Supprimer définitivement l’accès à mon compte",
    })
    .click();
  await expect(
    page.getByRole("heading", { name: "Compte supprimé" }),
  ).toBeVisible();
  await expect(page.getByText("demande-test", { exact: true })).toBeVisible();
});
