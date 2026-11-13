import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

async function publicSession(page: Page) {
  await page.route("**/api/**", (route) =>
    route.fulfill(
      new URL(route.request().url()).pathname.endsWith("/auth/me")
        ? { status: 401, json: { detail: "Connexion requise" } }
        : { json: { setup_required: false, registration_open: true } },
    ),
  );
}
const canvas = (page: Page) => page.getByTestId("experience-canvas");
const altitude = async (page: Page) =>
  Number(await canvas(page).getAttribute("data-camera-y"));
async function seek(page: Page, percent: number) {
  await page
    .getByRole("slider", { name: "Position dans le récit" })
    .fill(String(percent));
  await expect
    .poll(async () => Number(await canvas(page).getAttribute("data-progress")))
    .toBeCloseTo(percent / 100, 3);
}
async function ready(page: Page) {
  await expect(page.locator(".sx-stage")).toHaveClass(/sx-stage--ready/, {
    timeout: 45000,
  });
}

test("continuous camera, native wheel reversal, resize and strictly local resources", async ({
  page,
}) => {
  const errors: string[] = [],
    external: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error" && !message.text().includes("401"))
      errors.push(message.text());
  });
  page.on("request", (request) => {
    if (!/^(127\.0\.0\.1|localhost)$/.test(new URL(request.url()).hostname))
      external.push(request.url());
  });
  await publicSession(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await ready(page);
  await expect(canvas(page)).toHaveAttribute("data-camera-y", "2.100");
  await page.mouse.wheel(0, 1600);
  await expect.poll(() => altitude(page)).toBeGreaterThan(10);
  const raised = await altitude(page);
  await page.mouse.wheel(0, -800);
  await expect.poll(() => altitude(page)).toBeLessThan(raised - 1);
  await seek(page, 8.3);
  const middle = await altitude(page);
  expect(middle).toBeGreaterThan(12);
  expect(middle).toBeLessThan(34);
  expect(
    Number(await canvas(page).getAttribute("data-draw-calls")),
  ).toBeLessThan(90);
  await page.setViewportSize({ width: 1024, height: 768 });
  await expect.poll(() => altitude(page)).toBeCloseTo(middle, 0);
  await page.setViewportSize({ width: 1100, height: 760 });
  await seek(page, 100);
  await expect.poll(() => altitude(page)).toBeCloseTo(2.5);
  await expect(
    page.getByRole("link", { name: "Commencer l’expérience Symbiose" }),
  ).toHaveAttribute("href", "/connexion");
  expect(
    (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze())
      .violations,
  ).toEqual([]);
  await seek(page, 0);
  await page.locator("#main-content").focus();
  await page.keyboard.press("PageDown");
  await expect.poll(() => altitude(page)).toBeGreaterThan(2.2);
  expect(errors).toEqual([]);
  expect(external).toEqual([]);
});

test("presentation yields to input and leaving the landing disposes its engine", async ({
  page,
}) => {
  await publicSession(page);
  await page.goto("/");
  await ready(page);
  await page.getByRole("button", { name: "Mode exploration" }).click();
  await page.getByRole("button", { name: "Lire le récit" }).click();
  await expect.poll(() => altitude(page)).toBeGreaterThan(2.11);
  await page.getByRole("button", { name: "Mettre en pause" }).focus();
  await page.keyboard.press("Space");
  await expect(
    page.getByRole("button", { name: "Lire le récit" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Lire le récit" }).click();
  await page.mouse.wheel(0, 200);
  await expect(
    page.getByRole("button", { name: "Lire le récit" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Accéder à l’application" }).click();
  await expect(page).toHaveURL(/\/connexion$/);
  await expect(page.locator(".sx-stage,.sx-canvas")).toHaveCount(0);
  expect(
    await page.evaluate(() => getComputedStyle(document.body).overflow),
  ).not.toBe("hidden");
  await page.goBack();
  await ready(page);
  await expect(page.locator(".sx-canvas canvas")).toHaveCount(1);
});

test("reduced motion uses eight fixed viewpoints, responsive layout and accessible dialog", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await publicSession(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await ready(page);
  await expect(canvas(page)).toHaveAttribute("data-camera-y", "2.100");
  await expect(
    page.getByText("Mouvements réduits · points de vue fixes"),
  ).toBeVisible();
  await page.getByRole("slider").fill("5");
  await expect(canvas(page)).toHaveAttribute("data-camera-y", "2.100");
  await page.getByRole("slider").fill("20");
  await expect(canvas(page)).toHaveAttribute("data-camera-y", "65.000");
  await page.getByRole("button", { name: "Mode exploration" }).click();
  await expect(page.getByRole("button", { name: "Lire le récit" })).toHaveCount(
    0,
  );
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("slider").fill("0");
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await expect(page.locator(".sx-experience")).toHaveAttribute(
    "data-reduced-motion",
    "false",
  );
  expect(
    (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze())
      .violations,
  ).toEqual([]);
  await page.getByRole("button", { name: "Le projet", exact: true }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page
    .getByRole("button", { name: "Réduire les mouvements", exact: true })
    .click();
  await expect(page.locator(".sx-experience")).toHaveAttribute(
    "data-reduced-motion",
    "true",
  );
  await expect(
    page.getByRole("button", { name: "Pitch chronométré" }),
  ).toBeVisible();
  expect(
    (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze())
      .violations,
  ).toEqual([]);
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).not.toBeVisible();
});

test("DEBUG seeks seven reversible transitions and changes actual draw layers", async ({
  page,
}) => {
  test.setTimeout(90000);
  await publicSession(page);
  await page.goto("/?debug=transitions&transition=immersion&p=0.5");
  await ready(page);
  const state = () =>
    canvas(page).evaluate((el) =>
      JSON.parse((el as HTMLElement).dataset.state!),
    );
  await expect.poll(async () => (await state()).transition).toBe("immersion");
  const select = page.getByLabel("Transition à inspecter"),
    slider = page.getByLabel("Progression de la transition");
  const ids = await select
    .locator("option")
    .evaluateAll((options) =>
      options.map((option) => (option as HTMLOptionElement).value),
    );
  expect(ids).toHaveLength(7);
  for (const id of ids) {
    await select.selectOption(id);
    let middle: number[] = [];
    const option = select.locator(`option[value="${id}"]`),
      start = Number(await option.getAttribute("data-start")),
      end = Number(await option.getAttribute("data-end"));
    for (const p of [0, 0.25, 0.5, 0.75, 1, 0.5]) {
      await slider.fill(String(p));
      await expect
        .poll(async () => (await state()).progress)
        .toBeCloseTo((start + (end - start) * p) / 210, 4);
      const pose = (await state()).position;
      expect(pose.every(Number.isFinite)).toBe(true);
      if (p === 0.5) {
        if (middle.length)
          expect(
            Math.hypot(...pose.map((v: number, i: number) => v - middle[i])),
          ).toBeLessThan(0.08);
        else middle = pose;
      }
    }
  }
  await select.selectOption("observation-data");
  await slider.fill("0.5");
  await expect(page.getByText("Confiance : non calculée")).toBeVisible();
  const before = (await state()).drawCalls;
  await page.getByLabel("Végétation / arbres et plantes").uncheck();
  await expect.poll(async () => (await state()).drawCalls).toBeLessThan(before);
  await page.getByLabel("Référence générée (fixe)").check();
  await expect(page.locator(".sx-debug-reference img")).toBeVisible();
});

test("failed asynchronous material is explicit and world remains usable", async ({
  page,
}) => {
  await publicSession(page);
  await page.route(
    "**/experience-models/forest_ground_04-Diffuse.jpg",
    (route) => route.fulfill({ status: 404, body: "Missing test fixture" }),
  );
  await page.goto("/?debug=transitions");
  await ready(page);
  await expect(
    page.getByText(/Calques indisponibles :.*forest_ground_04/),
  ).toBeVisible();
  await page.getByLabel("Progression de la transition").fill("0.5");
  await expect.poll(() => altitude(page)).toBeGreaterThan(12);
});

test("WebGL failure uses reversible spatial masks and real application links", async ({
  page,
}) => {
  await publicSession(page);
  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (
      type: any,
      ...args: any[]
    ) {
      if (type === "webgl2") return null;
      return original.call(this, type, ...args);
    } as typeof original;
  });
  await page.goto("/?debug=transitions");
  await expect(page.locator(".sx-fallback-note")).toContainText(
    "2D simplifiée",
  );
  await expect(page.getByTestId("experience-fallback")).toBeVisible();
  const slider = page.getByLabel("Progression de la transition");
  await slider.fill("0.5");
  await expect
    .poll(() =>
      page.locator(".sx-fallback-scene img").nth(1).getAttribute("style"),
    )
    .toContain("50");
  await slider.fill("0");
  await expect
    .poll(() =>
      page.locator(".sx-fallback-scene img").nth(1).getAttribute("style"),
    )
    .toContain("100%");
  await page.locator(".sx-debug-panel summary").click();
  await page
    .getByRole("button", { name: "Lire le projet et le parcours" })
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.getByRole("link", { name: "Se connecter", exact: true }).click();
  await expect(page).toHaveURL(/\/connexion$/);
});

test("context loss releases WebGL and resumes with a current 2D inspector", async ({
  page,
}) => {
  await publicSession(page);
  await page.goto("/?debug=transitions&transition=observation-data&p=0.4");
  await ready(page);
  await page.locator(".sx-canvas canvas").evaluate((element) => {
    const gl = (element as HTMLCanvasElement).getContext("webgl2");
    const extension = gl?.getExtension("WEBGL_lose_context");
    if (!extension) throw new Error("Context-loss test extension unavailable");
    extension.loseContext();
  });
  await expect(page.getByTestId("experience-fallback")).toBeVisible();
  await expect(page.locator(".sx-canvas canvas")).toHaveCount(0);
  await expect(page.getByText("Confiance : non calculée")).toHaveCount(0);
  await page.getByLabel("Transition à inspecter").selectOption("ascent");
  await page.getByLabel("Progression de la transition").fill("0");
  await expect(page.getByLabel("Caméra inspectée")).toContainText(
    "0.00 / 2.10 / 18.00",
  );
});
