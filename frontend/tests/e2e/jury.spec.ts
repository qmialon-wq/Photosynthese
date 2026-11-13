import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("software renderer automatically releases WebGL and keeps the complete jury", async ({
  playwright,
  baseURL,
}) => {
  const browser = await playwright.chromium.launch({
    args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
  });
  try {
    const page = await browser.newPage();
    await page.goto(`${baseURL}/jury/`);
    await expect(page.getByTestId("experience-fallback")).toBeVisible();
    await expect(page.locator(".sx-canvas")).toHaveCount(0);
    await expect(
      page.getByText("Le rendu graphique logiciel est trop lent", {
        exact: false,
      }),
    ).toBeVisible();
    await page.keyboard.press("End");
    await expect(page.locator(".sx-pitch-content")).toHaveAttribute(
      "data-chapter",
      "night-forest",
    );
    await expect(
      page.getByRole("link", { name: "Commencer l’expérience Symbiose" }),
    ).toHaveAttribute("href", "/connexion");
  } finally {
    await browser.close();
  }
});

test("standalone jury starts without any authentication or business API", async ({
  page,
}) => {
  const api: string[] = [],
    errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.route("**/api/**", (route) => {
    api.push(route.request().url());
    return route.abort();
  });
  await page.goto("/jury/");
  await expect(page.locator(".sx-stage")).toHaveClass(/sx-stage--ready/, {
    timeout: 45000,
  });
  await expect(
    page.getByRole("button", { name: "Mode présentation", exact: true }),
  ).toBeVisible();
  await page.keyboard.press("ArrowRight");
  await expect(page.locator(".sx-pitch-content")).toHaveAttribute(
    "data-chapter",
    "sky",
  );
  await expect(page.locator(".sx-counter")).toHaveText("0:35 / 5:00");
  expect(api).toEqual([]);
  expect(errors).toEqual([]);
});

test("jury recovers a saved chapter and supports immediate skip, restart and 2D rescue", async ({
  page,
}) => {
  await page.goto("/jury/");
  await expect(page.locator(".sx-stage")).toHaveClass(/sx-stage--ready/, {
    timeout: 45000,
  });
  await page.getByRole("button", { name: "3. Rivières" }).click();
  await expect(page.locator(".sx-pitch-content")).toHaveAttribute(
    "data-chapter",
    "rivers",
  );
  await page.reload();
  await expect(page.locator(".sx-stage")).toHaveClass(/sx-stage--ready/, {
    timeout: 45000,
  });
  await page.getByText("Régie du récit", { exact: true }).click();
  await page
    .getByRole("button", { name: "Reprendre : Les données", exact: true })
    .click();
  await expect(page.locator(".sx-pitch-content")).toHaveAttribute(
    "data-chapter",
    "rivers",
  );
  await page
    .getByRole("button", { name: "Passer l’animation", exact: true })
    .click();
  await expect(page.locator(".sx-pitch-content")).toHaveAttribute(
    "data-chapter",
    "underwater",
  );
  await page
    .getByRole("button", { name: "Secours sans WebGL", exact: true })
    .click();
  await expect(page.getByTestId("experience-fallback")).toBeVisible();
  await expect(page.locator(".sx-canvas")).toHaveCount(0);
  await page
    .getByRole("button", { name: "Recommencer le récit", exact: true })
    .click();
  await expect(page.locator(".sx-pitch-content")).toHaveAttribute(
    "data-chapter",
    "forest",
  );
});

test("forced 2D never creates a WebGL context and keeps the sources and application CTA", async ({
  page,
}) => {
  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext;
    (window as any).webglAttempts = 0;
    HTMLCanvasElement.prototype.getContext = function (
      type: any,
      ...args: any[]
    ) {
      if (type === "webgl2") {
        (window as any).webglAttempts++;
        throw new Error("No GPU allowed");
      }
      return original.call(this, type, ...args);
    } as typeof original;
  });
  await page.goto("/jury/?render=2d");
  await expect(page.getByTestId("experience-fallback")).toBeVisible();
  await page.getByRole("button", { name: "8. Forêt nocturne" }).click();
  await expect(
    page.getByRole("link", { name: "Commencer l’expérience Symbiose" }),
  ).toHaveAttribute("href", /connexion/);
  await page.getByRole("button", { name: "Sources et texte oral" }).click();
  await expect(
    page.getByRole("heading", { name: /Les preuves, les mots/ }),
  ).toBeVisible();
  expect(await page.evaluate(() => (window as any).webglAttempts)).toBe(0);
  expect(
    (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze())
      .violations,
  ).toEqual([]);
});

test("installed production jury reloads all eight chapters and sources with the network offline", async ({
  page,
  context,
}) => {
  test.skip(
    !process.env.E2E_PRODUCTION,
    "Service worker emitted by the production build only",
  );
  test.setTimeout(90000);
  const api: string[] = [];
  await page.route("**/api/**", (route) => {
    api.push(route.request().url());
    return route.abort();
  });
  await page.goto("/jury/?render=2d");
  await page.getByText("Préparation du jury", { exact: false }).first().click();
  await page
    .getByRole("button", { name: "Installer hors ligne", exact: true })
    .click();
  await expect(
    page.getByRole("status").filter({ hasText: "Installation locale prête" }),
  ).toBeVisible({ timeout: 65000 });
  await context.setOffline(true);
  await page.reload();
  await expect(page.getByTestId("experience-fallback")).toBeVisible();
  for (let index = 0; index < 8; index++) {
    await page.locator(".sx-chapter-nav button").nth(index).click();
    await expect(page.locator(".sx-pitch-scene h2")).toHaveCount(1);
    await expect(page.locator(".sx-fallback-scene [role=status]")).toHaveCount(
      0,
    );
    await page
      .locator(".sx-fallback-scene img")
      .evaluateAll((images) =>
        Promise.all(
          images.map((image) => (image as HTMLImageElement).decode()),
        ),
      );
    await expect(page.locator(".sx-fallback-scene [role=alert]")).toHaveCount(
      0,
    );
  }
  await page.getByRole("button", { name: "Sources et texte oral" }).click();
  await page
    .getByRole("button", { name: "Attendus du jury", exact: true })
    .click();
  await expect(page.getByRole("table")).toBeVisible();
  expect(api).toEqual([]);
  await page.screenshot({ path: "../output/symbiose/final/jury-offline.png" });
});
