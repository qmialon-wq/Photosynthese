import { expect, type Page } from "@playwright/test";

export async function loginLive(page: Page) {
  const email = process.env.BIOSENTINELLE_E2E_EMAIL;
  const password = process.env.BIOSENTINELLE_E2E_PASSWORD;
  if (!email || !password)
    throw new Error(
      "Définir BIOSENTINELLE_E2E_EMAIL et BIOSENTINELLE_E2E_PASSWORD pour un compte de test autorisé.",
    );
  await page.goto("/connexion");
  await page.getByLabel("Adresse e-mail").fill(email);
  await page.getByLabel("Mot de passe", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Connexion", exact: true }).click();
  await expect(page).toHaveURL(/\/$/);
}
