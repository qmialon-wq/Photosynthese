// Visual evidence only: explicit HTTP fixtures, no real account or server login.
// Run against Vite: node scripts/record-login-transition.mjs http://127.0.0.1:4173
import { chromium, expect } from "@playwright/test";
import { mkdir, rename } from "node:fs/promises";
import { fileURLToPath } from "node:url";

const baseURL = process.argv[2] || "http://127.0.0.1:4173";
const output = fileURLToPath(
  new URL("../../output/symbiose/etape-17/", import.meta.url),
);
await mkdir(output, { recursive: true });
const browser = await chromium.launch();
try {
  for (const [name, viewport] of [
    ["desktop", { width: 1600, height: 900 }],
    ["mobile", { width: 390, height: 844 }],
  ]) {
    const context = await browser.newContext({
      baseURL,
      viewport,
      reducedMotion: "no-preference",
      recordVideo: { dir: output, size: viewport },
    });
    try {
      const page = await context.newPage();
      let connected = false;
      const session = {
        user: {
          id: "recording",
          email: "camille@example.test",
          display_name: "Camille",
          role: "client",
          created_at: "2026-11-10T10:00:00Z",
          deleted_at: null,
        },
        csrf_token: "recording-fixture",
      };
      await page.route("**/api/**", (route) => {
        const path = new URL(route.request().url()).pathname;
        if (path.endsWith("/auth/login")) {
          connected = true;
          return route.fulfill({ json: session });
        }
        if (path.endsWith("/auth/me"))
          return route.fulfill(
            connected
              ? { json: session }
              : { status: 401, json: { detail: "Connexion requise" } },
          );
        if (path.endsWith("/auth/status"))
          return route.fulfill({ json: { setup_required: false } });
        return route.fulfill({
          status: 503,
          json: {
            detail:
              "Données indisponibles — enregistrement avec réponses HTTP de test",
          },
        });
      });
      await page.goto("/connexion");
      await page.getByLabel("Adresse e-mail").fill(session.user.email);
      await page
        .getByLabel("Mot de passe", { exact: true })
        .fill("phrase-de-passe-test");
      await page.waitForTimeout(600);
      await page
        .getByRole("button", { name: "Se connecter", exact: true })
        .click();
      // No screenshots, animation pauses or per-frame probes during this take.
      await page.waitForTimeout(3500);
      await expect(page).toHaveURL(/\/$/);
      await expect(page.getByTestId("login-transition")).toHaveCount(0);
      await expect(
        page.getByRole("heading", { name: "Accueil Symbiose" }),
      ).toBeVisible();
      const video = page.video();
      await context.close();
      await rename(await video.path(), `${output}parcours-${name}.webm`);
      console.log(`Enregistrement continu : parcours-${name}.webm`);
    } finally {
      await context.close();
    }
  }
} finally {
  await browser.close();
}
