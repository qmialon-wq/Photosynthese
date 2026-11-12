import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { LOGIN_TRANSITION_MS } from "../../src/composables/useLoginTransition";

const session = {
  user: {
    id: "transition-client",
    email: "camille@example.test",
    display_name: "Camille",
    role: "client",
    created_at: "2026-11-10T10:00:00Z",
    deleted_at: null,
  },
  csrf_token: "transition-csrf",
};
async function mockApi(
  page: Page,
  login: "success" | "refused" | "offline" = "success",
  gate?: Promise<void>,
) {
  let connected = false;
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/auth/me")
      return route.fulfill(
        connected
          ? { json: session }
          : { status: 401, json: { detail: "Connexion requise" } },
      );
    if (path === "/api/auth/status")
      return route.fulfill({ json: { setup_required: false } });
    if (path === "/api/auth/login") {
      await gate;
      if (login === "offline") return route.abort("connectionrefused");
      if (login === "refused")
        return route.fulfill({
          status: 401,
          json: { detail: "Identifiants incorrects" },
        });
      connected = true;
      return route.fulfill({ json: session });
    }
    if (path === "/api/auth/logout") {
      connected = false;
      return route.fulfill({ status: 204 });
    }
    // Business data is deliberately unavailable: it must not hold the transition open.
    return route.fulfill({
      status: 503,
      json: { detail: "Données temporairement indisponibles" },
    });
  });
}
async function fillLogin(page: Page) {
  await page.goto("/connexion");
  await page.getByLabel("Adresse e-mail").fill("camille@example.test");
  await page
    .getByLabel("Mot de passe", { exact: true })
    .fill("phrase-de-passe-test");
}
const overlay = (page: Page) => page.getByTestId("login-transition");
async function submit(page: Page) {
  await page.getByRole("button", { name: "Se connecter", exact: true }).click();
}

test.use({
  viewport: { width: 1600, height: 900 },
  video: { mode: "on", size: { width: 1600, height: 900 } },
});

test("connexion rapide : galop articulé, Accueil en arrière-plan, révélation et déconnexion", async ({
  page,
}, info) => {
  await mockApi(page);
  await fillLogin(page);
  await submit(page);
  await expect(overlay(page)).toBeVisible();
  await expect(page).toHaveURL(/\/$/);
  await expect(
    page.getByRole("status").filter({ hasText: "Connexion réussie" }),
  ).toHaveCount(1);
  const leg = page.locator(".deer-front.deer-near");
  const before = await leg.evaluate((el) => getComputedStyle(el).transform);
  await page.waitForTimeout(85);
  const after = await leg.evaluate((el) => getComputedStyle(el).transform);
  expect(before).not.toBe(after);
  expect(
    await page
      .locator(".deer-front-shin")
      .first()
      .evaluate((el) => el.getAnimations().length),
  ).toBeGreaterThan(0);
  await expect(page.locator(".login-deer")).toHaveAttribute(
    "aria-hidden",
    "true",
  );
  await page.screenshot({ path: info.outputPath("galop-1600x900.png") });
  await expect(overlay(page)).toHaveCount(0, {
    timeout: LOGIN_TRANSITION_MS + 600,
  });
  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "Vos observations, simplement.",
    }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "Vos observations, simplement.",
    }),
  ).toBeVisible();
  await expect(overlay(page)).toHaveCount(0);
  await page.goto("/videos");
  await page.getByRole("button", { name: "Mon profil", exact: true }).click();
  await page
    .getByRole("button", { name: "Se déconnecter", exact: true })
    .click();
  await expect(page).toHaveURL(/\/connexion$/);
  await expect(overlay(page)).toHaveCount(0);
});

for (const result of ["refused", "offline"] as const) {
  test(`pas de transition si connexion ${result}`, async ({ page }) => {
    await mockApi(page, result);
    await fillLogin(page);
    await submit(page);
    await expect(page.getByRole("alert")).toBeVisible();
    await expect(page).toHaveURL(/\/connexion$/);
    await expect(overlay(page)).toHaveCount(0);
    await expect(
      page.getByRole("button", { name: "Se connecter", exact: true }),
    ).toBeEnabled();
  });
}

test("réponse lente : aucune réussite avant le serveur ; Passer au clavier conserve la session", async ({
  page,
}) => {
  let release!: () => void;
  await mockApi(
    page,
    "success",
    new Promise<void>((resolve) => {
      release = resolve;
    }),
  );
  await fillLogin(page);
  await submit(page);
  await expect(
    page.getByRole("button", { name: "Veuillez patienter…" }),
  ).toBeDisabled();
  await page.waitForTimeout(650);
  await expect(overlay(page)).toHaveCount(0);
  release();
  const skip = page.getByRole("button", { name: "Passer" });
  await expect(skip).toBeFocused();
  await expect(page).toHaveURL(/\/$/);
  await page.keyboard.press("Enter");
  await expect(overlay(page)).toHaveCount(0);
  await expect(page.locator("#main-content")).toBeFocused();
  await page.goto("/videos");
  await page.getByRole("button", { name: "Mon profil", exact: true }).click();
  await expect(page.locator(".sym-action-panel")).toContainText("Camille");
});

test("Passer à la souris", async ({ page }) => {
  await mockApi(page);
  await fillLogin(page);
  await submit(page);
  await page.getByRole("button", { name: "Passer" }).click();
  await expect(overlay(page)).toHaveCount(0);
  await expect(page).toHaveURL(/\/$/);
});

for (const preference of ["system", "symbiose"] as const) {
  test(`réduction des animations : ${preference}`, async ({ page }) => {
    if (preference === "system")
      await page.emulateMedia({ reducedMotion: "reduce" });
    else
      await page.addInitScript(() =>
        localStorage.setItem("symbiose:reduce-motion:v1", "true"),
      );
    await mockApi(page);
    await fillLogin(page);
    // Observe even short-lived mounts rather than relying on a 120ms assertion window.
    await page.evaluate(() => {
      (window as unknown as { deerSeen: boolean }).deerSeen = false;
      new MutationObserver(() => {
        if (document.querySelector(".login-deer"))
          (window as unknown as { deerSeen: boolean }).deerSeen = true;
      }).observe(document.body, { childList: true, subtree: true });
    });
    await submit(page);
    await expect(page).toHaveURL(/\/$/);
    await expect(overlay(page)).toHaveCount(0, { timeout: 700 });
    expect(
      await page.evaluate(
        () => (window as unknown as { deerSeen: boolean }).deerSeen,
      ),
    ).toBe(false);
  });
}

test("navigation annulée : nettoyage immédiat et erreur permettant une nouvelle tentative", async ({
  page,
}) => {
  await mockApi(page);
  await fillLogin(page);
  await page.evaluate(async () => {
    const modulePath = "/src/router.ts";
    const { router } = await import(/* @vite-ignore */ modulePath);
    const remove = router.beforeEach((to: { path: string }) => {
      if (to.path === "/") {
        remove();
        return false;
      }
    });
  });
  await submit(page);
  await expect(page.getByRole("alert")).toContainText(
    "L’Accueil n’a pas pu être ouvert",
  );
  await expect(overlay(page)).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Se connecter", exact: true }),
  ).toBeEnabled();
  await page
    .getByLabel("Mot de passe", { exact: true })
    .fill("phrase-de-passe-test");
  await submit(page);
  await expect(page).toHaveURL(/\/$/);
  await expect(overlay(page)).toHaveCount(0, {
    timeout: LOGIN_TRANSITION_MS + 600,
  });
});

test("mobile : composition dans le viewport et absence de piège clavier", async ({
  page,
}, info) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockApi(page);
  await fillLogin(page);
  await submit(page);
  await expect(overlay(page)).toBeVisible();
  await expect(page.getByRole("button", { name: "Passer" })).toBeInViewport();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("button", { name: "Passer" })).not.toBeFocused();
  // Freeze the composition for the still capture and keyboard audit. The desktop
  // recording above runs in real time, including the complete gallop.
  await overlay(page).evaluate((el) => {
    for (const animation of el.getAnimations({ subtree: true })) {
      animation.pause();
      animation.currentTime =
        animation.effect?.getTiming().iterations === Infinity ? 320 : 1250;
    }
  });
  await page.screenshot({ path: info.outputPath("galop-390x844.png") });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await overlay(page).evaluate((el) => {
    for (const animation of el.getAnimations({ subtree: true }))
      animation.play();
  });
  await expect(overlay(page)).toHaveCount(0, {
    timeout: LOGIN_TRANSITION_MS + 600,
  });
  expect(
    (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze())
      .violations,
  ).toEqual([]);
});

for (const [theme, expectedPrimary] of Object.entries({
  forest: "#0b3829",
  sky: "#122b4c",
  river: "#103847",
  underwater: "#082b46",
  wetland: "#15382f",
  meadow: "#35412a",
  coast: "#203d50",
  "night-forest": "#11192f",
})) {
  test(`palette de connexion ${theme}`, async ({ page }) => {
    await page.addInitScript(
      (id) => localStorage.setItem("symbiose:wallpaper:v1", id),
      theme,
    );
    await mockApi(page);
    await fillLogin(page);
    await submit(page);
    await expect(overlay(page)).toBeVisible();
    await expect(page.locator("html")).toHaveAttribute(
      "data-environment",
      theme,
    );
    const colors = await overlay(page).evaluate((el, primary) => {
      const sample = document.createElement("div");
      sample.style.backgroundColor = `color-mix(in srgb, ${primary} 92%, transparent)`;
      document.body.append(sample);
      const expected = getComputedStyle(sample).backgroundColor;
      sample.remove();
      return { actual: getComputedStyle(el).backgroundColor, expected };
    }, expectedPrimary);
    expect(colors.actual).toBe(colors.expected);
    await page.getByRole("button", { name: "Passer" }).click();
    await expect(overlay(page)).toHaveCount(0);
    await page
      .getByRole("link", { name: "Importer une vidéo", exact: true })
      .click();
    await expect(page).toHaveURL(/\/videos$/);
    await expect(overlay(page)).toHaveCount(0);
  });
}
