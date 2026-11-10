import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { mkdir } from "node:fs/promises";
import { readFileSync } from "node:fs";
import { openDisplaySettings } from "./display-settings";

// Real deterministic engine output with synthetic project inputs and empty map fixtures.
const designFixture = JSON.parse(
  readFileSync(
    new URL("../fixtures/territorial-design.json", import.meta.url),
    "utf8",
  ),
);

const corpus = "22222222-2222-4222-8222-222222222222";
const base = `/parcels/corpora/${corpus}`;
const profile = {
  area_m2: 2500,
  land_type: "pasture",
  project_type: "housing",
  locality: "Recette navigateur — données de test",
  details: "Projet de recette",
  interventions: [] as string[],
};
const location = {
  latitude: 49.316,
  longitude: -1.235,
  revision: 1,
  provenance: "numeric",
  actor: "owner",
  created_at: "2026-11-10T10:00:00Z",
};
async function fixture(page: Page, mode = "real") {
  await page.addInitScript(
    (value) => localStorage.setItem("symbiose:data-mode:v1", value),
    mode,
  );
  let saved = structuredClone(profile),
    revision = 1,
    point: typeof location | null = null;
  let query: Record<string, unknown> | null = null;
  const calls: string[] = [];
  await page.route("https://tile.openstreetmap.org/**", (route) =>
    route.abort(),
  );
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname.replace("/api", "");
    calls.push(path);
    if (path === "/auth/me")
      return route.fulfill({
        json: {
          user: {
            id: "owner",
            role: "client",
            display_name: "Recette",
            email: null,
            created_at: "2026-11-10",
          },
          csrf_token: "test",
        },
      });
    if (path === base + "/profile" && route.request().method() === "PUT") {
      expect(route.request().headers()["x-csrf-token"]).toBe("test");
      const body = route.request().postDataJSON();
      expect(body.area_m2).toBe(saved.area_m2);
      expect(body.project_type).toBe(saved.project_type);
      expect(body.expected_revision).toBe(revision);
      saved.interventions = body.interventions;
      revision++;
      if (query) query.obsolete = true;
      return route.fulfill({ json: { revision, profile: saved } });
    }
    if (path === base + "/location") {
      point = location;
      return route.fulfill({ json: point });
    }
    if (path === base + "/territorial-queries") {
      query = {
        id: "q-test",
        revision,
        status: "complete",
        obsolete: false,
        created_at: location.created_at,
        input_sha256: "fixture-test-only",
        layers: {
          znieff1: { status: "empty", retrieved_at: location.created_at },
        },
        inputs: {
          location,
          profile: structuredClone(saved),
          profile_revision: revision,
          observations: [],
        },
        result: {
          ...structuredClone(designFixture),
          analysis_revision: revision,
          facts: designFixture.facts.filter(
            (fact: { id: string }) =>
              !fact.id.startsWith("project:") ||
              saved.interventions.some((code) => fact.id === "project:" + code),
          ),
          actions: designFixture.actions.filter(
            (action: { project_action: string }) =>
              saved.interventions.includes(action.project_action),
          ),
          project_concerns: designFixture.project_concerns.filter(
            (item: { project_action: string }) =>
              saved.interventions.includes(item.project_action),
          ),
          design_proposals: designFixture.design_proposals.filter(
            (item: { project_action: string }) =>
              saved.interventions.includes(item.project_action),
          ),
        },
      };
      return route.fulfill({
        status: 202,
        json: { id: "q-test", status: "pending" },
      });
    }
    if (path === base + "/territorial-context/export")
      return route.fulfill({
        json: query,
        headers: {
          "Content-Disposition": 'attachment; filename="project-test.json"',
        },
      });
    if (path === base + "/territorial-context")
      return route.fulfill({
        json: {
          location: point,
          profile: saved,
          profile_revision: revision,
          query,
        },
      });
    if (path === base)
      return route.fulfill({
        json: {
          id: corpus,
          actor: "owner",
          videos: [],
          profile: { revision, profile: saved },
          dossier: null,
        },
      });
    if (path === "/parcels/options")
      return route.fulfill({
        json: {
          land_types: { pasture: "Pâturage" },
          project_types: { housing: "Habitation" },
        },
      });
    return route.fulfill({ json: [] });
  });
  return calls;
}

test("propriétaire : point, interventions, analyse, export et formulaire modifiable", async ({
  page,
}) => {
  await fixture(page);
  await page.goto(`/parcelles/${corpus}`);
  await expect(
    page.getByRole("heading", { name: "Analyse préliminaire du projet" }),
  ).toBeVisible();
  await expect(page.getByLabel("Surface de la parcelle (m²)")).toHaveValue(
    "2500",
  );
  await page
    .locator(".territorial-point-map")
    .click({ position: { x: 100, y: 100 } });
  await expect(page.getByLabel("Latitude WGS84")).not.toHaveValue("");
  await expect(
    page.locator(".territorial-point-map .leaflet-interactive"),
  ).toHaveCount(1);
  await page.getByLabel("Latitude WGS84").fill("49.316");
  await page.getByLabel("Longitude WGS84").fill("-1.235");
  await page
    .getByRole("button", {
      name: "Enregistrer le point et préremplir",
      exact: true,
    })
    .click();
  await page.getByLabel("Clôture", { exact: true }).check();
  await page
    .getByRole("button", { name: "Enregistrer mes modifications", exact: true })
    .click();
  await page
    .getByRole("button", {
      name: "Consulter les données territoriales et analyser le projet",
    })
    .click();
  await page
    .getByText(
      "Vérifications complémentaires et propositions issues des preuves",
      { exact: true },
    )
    .click();
  await expect(
    page.getByText("VÉRIFICATION GÉNÉRALE", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Compenser : non évalué.", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", {
      name: "Exporter l’analyse et ses preuves (JSON)",
    }),
  ).toHaveAttribute(
    "href",
    new RegExp("territorial-context/export\\?revision=2$"),
  );
  const scan = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa"])
    .analyze();
  expect(
    scan.violations.map((v) => ({
      id: v.id,
      targets: v.nodes.map((n) => n.target),
    })),
  ).toEqual([]);
  await mkdir("../output/playwright", { recursive: true });
  await page.screenshot({
    path: "../output/playwright/territorial-owner-design-test-fixture.png",
    fullPage: true,
  });
  await page.reload();
  await expect(page.getByLabel("Clôture", { exact: true })).toBeChecked();
  // Switching a private dossier back to demo navigates away and removes this panel.
  await (await openDisplaySettings(page)).selectOption("demo");
  await expect(
    page.getByRole("heading", { name: "Mes dossiers", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("VÉRIFICATION GÉNÉRALE", { exact: true }),
  ).toHaveCount(0);
});

test("démonstration : aucune requête territoriale avec un identifiant fictif", async ({
  page,
}) => {
  const calls = await fixture(page, "demo");
  await page.goto("/parcelles/demo-corpus");
  await expect(
    page.getByText(/Aucune requête territoriale n’est envoyée/),
  ).toBeVisible();
  expect(calls.some((path) => path.startsWith("/parcels/"))).toBe(false);
});

test("A/B : adapter les interventions change les alternatives et leur export", async ({
  page,
}) => {
  await fixture(page);
  await page.goto(`/parcelles/${corpus}`);
  await page.getByLabel("Latitude WGS84").fill("49.316");
  await page.getByLabel("Longitude WGS84").fill("-1.235");
  await page
    .getByRole("button", {
      name: "Enregistrer le point et préremplir",
      exact: true,
    })
    .click();
  await page.getByLabel("Éclairage extérieur", { exact: true }).check();
  await page
    .getByRole("button", { name: "Enregistrer mes modifications", exact: true })
    .click();
  await page
    .getByRole("button", {
      name: "Consulter les données territoriales et analyser le projet",
    })
    .click();
  const options = page.getByRole("region", {
    name: "Adapter mon projet",
    exact: true,
  });
  await expect(
    options.locator('[data-intervention="outdoor_lighting"]'),
  ).toBeVisible();
  await expect(options.locator('[data-intervention="fencing"]')).toHaveCount(0);
  await expect(
    options.getByRole("heading", {
      name: "Réduire la durée de fonctionnement",
    }),
  ).toBeVisible();
  await expect(options.locator(".design-option")).toHaveCount(3);
  await page.getByLabel("Clôture", { exact: true }).check();
  await page
    .getByRole("button", { name: "Enregistrer mes modifications", exact: true })
    .click();
  await expect(
    page.getByRole("alert").filter({ hasText: "Analyse obsolète" }),
  ).toBeVisible();
  await page
    .getByRole("button", {
      name: "Consulter les données territoriales et analyser le projet",
    })
    .click();
  await expect(options.locator('[data-intervention="fencing"]')).toBeVisible();
  await expect(options.locator(".design-option")).toHaveCount(6);
  await expect(
    options.getByRole("heading", { name: "Limiter le périmètre clôturé" }),
  ).toBeVisible();
  const first = options.locator('[data-alternative="fencing:reroute"]');
  await expect(first).toContainText("Niveau de justification : Exploratoire");
  await expect(first).toContainText("Ce que cela changerait au projet");
  await first
    .getByText("Observations, sources mobilisées et limites", { exact: true })
    .click();
  await expect(first).toContainText("Référence générale de conception");
  await expect(first).toContainText("Intervention déclarée : Clôture");
  const exportLink = page.getByRole("link", {
    name: "Exporter l’analyse et ses preuves (JSON)",
  });
  const href = await exportLink.getAttribute("href");
  expect(href).toMatch(/territorial-context\/export\?revision=3$/);
  const exported = await page.evaluate(async (url) => {
    const response = await fetch(url);
    if (!response.ok) throw new Error("Échec export");
    return response.json();
  }, href!);
  expect(exported.inputs.profile.interventions).toEqual([
    "outdoor_lighting",
    "fencing",
  ]);
  expect(
    exported.result.design_proposals
      .map((p: { project_action: string }) => p.project_action)
      .sort(),
  ).toEqual(["fencing", "outdoor_lighting"]);
  expect(
    exported.result.design_proposals[0].alternatives[0].project_change,
  ).toBeTruthy();
  const scan = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa"])
    .analyze();
  expect(
    scan.violations.map((v) => ({
      id: v.id,
      targets: v.nodes.map((n) => n.target),
    })),
  ).toEqual([]);
  await mkdir("../output/playwright", { recursive: true });
  await page.screenshot({
    path: "../output/playwright/project-adaptation-test-fixture.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await options.scrollIntoViewIfNeeded();
  expect(
    await options.evaluate(
      (element) => element.scrollWidth <= element.clientWidth + 1,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "../output/playwright/project-adaptation-mobile-test-fixture.png",
    fullPage: true,
  });
  // Removing the initial intervention must remove its alternatives from the new analysis.
  await page.getByLabel("Éclairage extérieur", { exact: true }).uncheck();
  await page
    .getByRole("button", { name: "Enregistrer mes modifications", exact: true })
    .click();
  await page
    .getByRole("button", {
      name: "Consulter les données territoriales et analyser le projet",
    })
    .click();
  await expect(
    options.locator('[data-intervention="outdoor_lighting"]'),
  ).toHaveCount(0);
  await expect(options.locator(".design-option")).toHaveCount(3);
});
