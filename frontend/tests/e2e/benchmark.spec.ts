import { mockApi } from "./mock-api";
import { test, expect } from "@playwright/test";

test("benchmark des quatre modèles, labels provisoires et rapport accessibles", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const names = [
    "EfficientNetV2 B0",
    "EfficientNetV2 S",
    "ConvNeXt Tiny",
    "ResNet50",
  ];
  await mockApi(page, (route) => {
    const path = new URL(route.request().url()).pathname;
    const models = names.map((name, index) => ({
      id: `test-model-${index}`,
      name,
      metrics: {},
      metadata: {},
      active: false,
    }));
    return route.fulfill({
      json: path.endsWith("/comparisons")
        ? [
            {
              id: "test-comparison",
              created_at: "2026-10-22T12:00:00Z",
              dataset_version: "test-dataset-sha256",
              human_validated: false,
              protocol: { split: "val" },
              models: models.map((m, index) => ({
                model: { model_id: m.id, classifier_family: "supervised" },
                metrics: {
                  macro_f1: 0.2 + index / 10,
                  accuracy: 0.4 + index / 10,
                },
                coverage: 0.8,
                failure_rate: 0,
                mean_inference_ms: 12,
                error: null,
              })),
            },
          ]
        : path.endsWith("/models")
          ? models
          : [],
    });
  });
  await page.goto("/admin/evaluation");
  const table = page.getByRole("table", { name: /Résultats du benchmark/ });
  await expect(table.getByRole("row")).toHaveCount(5);
  for (const name of names)
    await expect(table.getByRole("link", { name, exact: true })).toBeVisible();
  await expect(
    page.getByText("Labels provisoires", { exact: true }),
  ).toBeVisible();
  await expect(
    table
      .getByRole("row")
      .filter({ hasText: "ResNet50" })
      .getByText("50.0 %", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Rapport JSON complet" }),
  ).toHaveAttribute("href", "/api/classification/comparisons/test-comparison");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.reload();
  await expect(table.getByRole("row")).toHaveCount(5);
  await table.getByRole("link", { name: "ResNet50", exact: true }).click();
  await expect(page.getByLabel("Modèle enregistré")).toHaveValue(
    "test-model-3",
  );
});
