import { test, expect } from "@playwright/test";

test("le corpus de base se sélectionne et soumet un véritable choix de source", async ({
  page,
}) => {
  let submitted = false;
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/training/datasets"))
      return route.fulfill({
        json: [
          {
            id: "base",
            name: "Corpus de base",
            source: "base",
            ready: true,
            video_count: 342,
            crop_count: 5000,
            warning:
              "Labels provisoires issus des noms ; les corrections humaines priment.",
          },
          {
            id: "a".repeat(64),
            name: "Validation terrain",
            source: "review",
            ready: true,
          },
          {
            id: "b".repeat(64),
            name: "Export en cours",
            source: "review",
            ready: false,
          },
        ],
      });
    if (path === "/api/console/training") {
      expect(route.request().postDataJSON().dataset_id).toBe("base");
      expect(
        route.request().postDataJSON().allow_filename_labels,
      ).toBeUndefined();
      submitted = true;
      return route.fulfill({
        json: { id: "11111111-1111-4111-8111-111111111111", status: "queued" },
      });
    }
    if (path.includes("/console/tasks/"))
      return route.fulfill({
        json: {
          id: "11111111-1111-4111-8111-111111111111",
          status: "queued",
          kind: "training",
          progress: {},
          request: { model_name: "tf_efficientnetv2_b0" },
        },
      });
    return route.fulfill({ json: [] });
  });
  await page.goto("/admin/training");
  await page.getByLabel("Dataset d’entraînement").selectOption("base");
  await expect(
    page.getByText("Corpus de base · 342 vidéos inventoriées", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText(/5000 recadrages préparés/)).toContainText(
    "Labels provisoires",
  );
  await expect(
    page.getByRole("option", { name: /Export en cours/ }),
  ).toHaveJSProperty("disabled", true);
  await page.getByRole("button", { name: "Démarrer l’entraînement" }).click();
  await expect.poll(() => submitted).toBe(true);
});

test("un corpus non préparé est visible mais désactivé", async ({ page }) => {
  await page.route("**/api/**", (route) =>
    route.fulfill({
      json: route.request().url().includes("/training/datasets")
        ? [
            {
              id: "base",
              name: "Corpus de base",
              source: "base",
              ready: false,
              unavailable_reason: "Exécuter make prepare-training DEVICE=cuda.",
            },
          ]
        : [],
    }),
  );
  await page.goto("/admin/training");
  await expect(
    page.getByRole("option", { name: /Corpus de base/ }),
  ).toHaveJSProperty("disabled", true);
  await expect(page.getByText(/Exécuter make prepare-training/)).toBeVisible();
});
