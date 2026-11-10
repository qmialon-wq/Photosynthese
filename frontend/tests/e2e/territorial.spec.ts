import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { mkdir } from "node:fs/promises";

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
  let query: unknown = null;
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
      expect(Object.keys(body).sort()).toEqual([
        "expected_revision",
        "interventions",
      ]);
      expect(body.expected_revision).toBe(revision);
      saved.interventions = body.interventions;
      revision++;
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
          rules_version: "territorial-erc-v1",
          analysis_revision: revision,
          facts: [
            {
              id: "project:fencing",
              kind: "user_declaration",
              text: "Intervention déclarée : Clôture.",
              source_refs: [],
            },
          ],
          project_concerns: [
            {
              project_action: "fencing",
              issue: "Conception et usages de la clôture",
              evidence_refs: ["project:fencing"],
            },
          ],
          actions: [
            {
              category: "investigate",
              project_action: "fencing",
              issue: "Conception et usages de la clôture",
              action: "Préciser le tracé et vérifier les déplacements réels.",
              rationale: "Vérification générale du projet de test.",
              evidence_refs: ["project:fencing"],
              source_refs: [],
              preconditions: ["Vérification sur site"],
              missing_information: ["Usages du projet"],
              limitations: ["Un point ne représente pas une parcelle"],
              evidence_status: "general_verification",
            },
          ],
          unknowns: ["Aucune espèce validée humainement."],
          limitations: [
            "Un résultat vide ne démontre aucune absence de biodiversité.",
          ],
          sources: [],
          compensation: { status: "not_assessed" },
        },
      };
      return route.fulfill({
        status: 202,
        json: { id: "q-test", status: "pending" },
      });
    }
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

test("propriétaire : point, interventions, analyse, export et formulaire historique verrouillé", async ({
  page,
}) => {
  await fixture(page);
  await page.goto(`/parcelles/${corpus}`);
  await expect(
    page.getByRole("heading", { name: "Analyse préliminaire du projet" }),
  ).toBeVisible();
  await expect(page.getByLabel("Surface de la parcelle (m²)")).toHaveCount(0);
  await expect(page.getByText("2500 m²", { exact: true })).toBeVisible();
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
    .getByRole("button", { name: "Enregistrer le point", exact: true })
    .click();
  await page.getByLabel("Clôture", { exact: true }).check();
  await page
    .getByRole("button", { name: "Enregistrer les interventions", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Consulter IGN et analyser le projet" })
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
    path: "../output/playwright/territorial-owner-test-fixture.png",
    fullPage: true,
  });
  await page.reload();
  await expect(page.getByLabel("Clôture", { exact: true })).toBeChecked();
  await page
    .getByLabel("Mode de données", { exact: true })
    .selectOption("demo");
  await expect(
    page.getByText(/Aucune requête territoriale n’est envoyée/),
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
