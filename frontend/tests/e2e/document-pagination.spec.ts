import { test, expect } from "@playwright/test";
import { mockApi } from "./mock-api";

test("pagination serveur, taille persistée et sélection limitée à la page", async ({
  page,
}) => {
  const offsets: number[] = [];
  await mockApi(page, (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === "/api/documents/species")
      return route.fulfill({
        json: [{ name: "renards", display_name: "Renard" }],
      });
    if (url.pathname === "/api/documents") {
      const offset = Number(url.searchParams.get("offset"));
      const limit = Number(url.searchParams.get("limit"));
      offsets.push(offset);
      return route.fulfill({
        json: Array.from(
          { length: Math.min(limit, 19 - offset) },
          (_, index) => ({
            id: `document-${offset + index}`,
            title: `Publication ${offset + index}`,
            status: "indexed",
            published_date: "2026-01-01",
            species_links: [{ species: "renards" }],
            assets: [],
          }),
        ),
      });
    }
    return route.fulfill({ json: [] });
  });
  await page.goto("/documents");
  await page.getByLabel("Documents par page").selectOption("4");
  await expect(page.locator(".sd-document-card")).toHaveCount(4);
  await page
    .getByLabel("Tout sélectionner sur cette page", { exact: true })
    .check();
  await expect(
    page.getByText("4 sélectionné(s)", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Page suivante", exact: true })
    .click();
  await expect(page.getByText("Page 2", { exact: true })).toBeVisible();
  await expect(
    page.getByText("0 sélectionné(s)", { exact: true }),
  ).toBeVisible();
  expect(offsets).toContain(4);
  await page.reload();
  await expect(page.getByLabel("Documents par page")).toHaveValue("4");
  await expect(
    page.getByRole("button", { name: "Page précédente", exact: true }),
  ).toBeDisabled();
});
