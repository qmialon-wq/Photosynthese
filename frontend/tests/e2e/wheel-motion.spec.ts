import { test, expect } from "@playwright/test";
import { mockApi } from "./mock-api";

for (const reducedMotion of ["reduce", "no-preference"] as const) {
  test(`navigation des pages authentifiées et retour à l'accueil connecté, animations ${reducedMotion}`, async ({
    page,
  }) => {
    await page.emulateMedia({ reducedMotion });
    await page.setViewportSize({ width: 1600, height: 900 });
    await mockApi(page, (route) => route.fulfill({ json: [] }));
    await page.goto("/videos");
    for (const path of [
      "/parcelles",
      "/analyses",
      "/review",
      "/documents",
      "/videos",
    ]) {
      await page.locator(`.sym-wheel-link[data-section="${path}"]`).click();
      await expect(page).toHaveURL(new RegExp(`${path}$`));
      await expect(page.locator(".sym-wheel")).toHaveAttribute(
        "data-motion",
        "idle",
      );
      await expect(
        page.locator('.sym-wheel-link[aria-current="page"]'),
      ).toHaveCount(1);
      const active = page.locator(`.sym-wheel-link[data-section="${path}"]`);
      await expect(active).toHaveAttribute("aria-current", "page");
      expect(
        await active
          .locator("svg")
          .evaluate((el) => getComputedStyle(el).transform),
      ).toBe("none");
    }
    await page.locator('.sym-wheel-link[data-section="/"]').click();
    await expect(page.getByRole("heading", { level: 1 })).toContainText(
      "Vos observations, simplement.",
    );
    await expect(page.locator(".sym-wheel")).toBeVisible();
    await expect(
      page.locator('.sym-wheel-link[data-section="/"]'),
    ).toHaveAttribute("aria-current", "page");
  });
}
