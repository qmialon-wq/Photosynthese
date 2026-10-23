import { test, expect } from "@playwright/test";

test("sélection directe d'un candidat sans dialogue ni validation, persistante au rechargement", async ({
  page,
}) => {
  let active = "current";
  let selections = 0;
  await page.route("**/api/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    if (
      route.request().method() === "POST" &&
      path.endsWith("/candidate/activate")
    ) {
      active = "candidate";
      selections += 1;
      return route.fulfill({ json: { id: active, active: true } });
    }
    return route.fulfill({
      json: path.endsWith("/models")
        ? ["current", "candidate", "archived"].map((id) => ({
            id,
            name: `Modèle ${id}`,
            active: id === active,
            status:
              id === active
                ? "active"
                : id === "archived"
                  ? "archived"
                  : "candidate",
            checkpoint_key: `${id}/best.pt`,
            sha256: "a".repeat(64),
            created_at: "2026-10-23T10:00:00Z",
            metadata: { model_name: "test-only", image_size: 224 },
            metrics: { validation: { macro_f1: 0.4, human_validated: false } },
          }))
        : [],
    });
  });
  await page.goto("/admin/models");
  const candidate = page.getByRole("article").filter({
    has: page.getByRole("heading", { name: "Modèle candidate", exact: true }),
  });
  const button = candidate.getByRole("button", { name: "Définir comme actif" });
  await expect(button).toBeEnabled();
  await expect(
    page
      .getByRole("article")
      .filter({ hasText: "Modèle archived" })
      .getByRole("button", { name: "Définir comme actif" }),
  ).toBeDisabled();
  await button.click();
  await expect(
    candidate.getByText("Modèle actif", { exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  expect(selections).toBe(1);
  await page.reload();
  await expect(
    candidate.getByText("Modèle actif", { exact: true }),
  ).toBeVisible();
  await expect(button).toBeDisabled();
  await expect(
    page.getByText(/validation humaine encore requise|Candidat à comparer/),
  ).toHaveCount(0);
});
