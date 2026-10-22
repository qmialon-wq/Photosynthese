import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
test("dashboard accessible, états vides et navigation au clavier", async ({
  page,
}) => {
  await page.route("**/api/**", (route) =>
    route.fulfill({
      json: route.request().url().includes("/dashboard")
        ? {
            counts: { videos: 0, species: 0, pending: 0, tasks: 0 },
            distribution: [],
            latest_training: null,
          }
        : [],
    }),
  );
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "La biodiversité, en perspective." }),
  ).toBeVisible();
  await expect(
    page.getByText("Aucune espèce confirmée pour le moment."),
  ).toBeVisible();
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Aller au contenu" }),
  ).toBeFocused();
  const scan = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(
    scan.violations.map((item) => ({
      id: item.id,
      nodes: item.nodes.map((node) => node.target),
    })),
  ).toEqual([]);
});
