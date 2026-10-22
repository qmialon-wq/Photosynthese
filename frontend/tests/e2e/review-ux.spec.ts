import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("accueil client simple et administration distincte", async ({ page }) => {
  await page.route("**/api/**", (route) => route.fulfill({ json: [] }));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Vos observations, simplement." }),
  ).toBeVisible();
  await expect(page.getByLabel("Nom de revue")).toHaveCount(0);
  const nav = page.getByRole("navigation", { name: "Navigation principale" });
  await expect(
    nav.getByRole("link", { name: "Entraînements", exact: true }),
  ).toHaveCount(0);
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
  await nav.getByRole("link", { name: "Administration", exact: true }).click();
  await expect(
    nav.getByRole("link", { name: "Entraînements", exact: true }),
  ).toHaveAttribute("href", "/admin/training");
  await expect(
    nav.getByRole("link", { name: "Espace observation", exact: true }),
  ).toBeVisible();
});

for (const conflict of [false, true]) {
  test(`validation multiple sans commentaire ${conflict ? "avec conflit explicite" : "persistante"}`, async ({
    page,
  }) => {
    const samples = [0, 1, 2].map((index) => ({
      id: `sample-${index}`,
      frame_index: index,
      original_name: "terrain.mp4",
      revision: 0,
      state: "pending",
      label: null as string | null,
      predicted_label: null,
      species_candidate: "chevreuil",
      box: { x: 0.1, y: 0.1, w: 0.5, h: 0.5 },
      split: index === 2 ? "test" : "train",
      test_locked: index === 2,
      render_status: "ready",
      quality: {},
      frame_quality: {},
      detection_score: 0.9,
    }));
    let submitted = false;
    await page.route("**/api/**", async (route) => {
      const url = new URL(route.request().url());
      if (url.pathname.endsWith("/review/species"))
        return route.fulfill({ json: [{ name: "renards", class_index: 5 }] });
      if (url.pathname.endsWith("/batch-decisions")) {
        const body = route.request().postDataJSON();
        expect(body.items).toEqual([
          { sample_id: "sample-0", expected_revision: 0 },
          { sample_id: "sample-1", expected_revision: 0 },
        ]);
        expect(body.label).toBe("renards");
        expect(body.reason).toBeUndefined();
        expect(route.request().headers()["x-reviewer"]).toMatch(/^local-/);
        submitted = true;
        if (conflict)
          return route.fulfill({
            status: 409,
            json: { detail: "Révision obsolète" },
          });
        for (const sample of samples.slice(0, 2))
          Object.assign(sample, {
            state: "corrected",
            label: "renards",
            revision: 1,
          });
        return route.fulfill({ json: samples.slice(0, 2) });
      }
      if (url.pathname.endsWith("/review/samples"))
        return route.fulfill({
          json: samples.filter(
            (s) => s.state === url.searchParams.get("state"),
          ),
        });
      if (url.pathname.includes("/images/"))
        return route.fulfill({
          contentType: "image/svg+xml",
          body: '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100" fill="#abc"/></svg>',
        });
      return route.fulfill({ json: [] });
    });
    await page.goto("/review");
    await page.getByLabel("Sélectionner la page", { exact: true }).check();
    await expect(
      page.getByLabel("Sélectionner terrain.mp4, image 2", { exact: true }),
    ).toBeDisabled();
    await page.getByLabel("Espèce à attribuer").selectOption("renards");
    await expect(
      page.getByRole("button", { name: "Valider la sélection" }),
    ).toBeEnabled();
    expect(
      (
        await new AxeBuilder({ page })
          .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
          .analyze()
      ).violations,
    ).toEqual([]);
    await page.getByRole("button", { name: "Valider la sélection" }).click();
    if (conflict) {
      await expect(page.getByRole("alert")).toContainText(
        "Aucune modification du lot",
      );
      await expect(
        page.getByLabel("Sélectionner terrain.mp4, image 0", { exact: true }),
      ).toBeChecked();
    } else {
      await expect(
        page.getByText("2 annotations enregistrées pour l’espèce renards.", {
          exact: true,
        }),
      ).toBeVisible();
      await page.reload();
      await page.getByLabel("État de validation").selectOption("corrected");
      await expect(
        page.getByRole("heading", { name: "renards", exact: true }),
      ).toHaveCount(2);
    }
    expect(submitted).toBe(true);
  });
}
