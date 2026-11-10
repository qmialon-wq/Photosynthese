import {
  openDisplaySettings,
  closeDisplaySettings,
  selectSource,
  expectSource,
} from "./display-settings";
import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";

const size = (page: Page) =>
  page.getByLabel("Documents par page", { exact: true });
const species = (page: Page) =>
  page.getByLabel("Espèce du corpus", { exact: true });
const cards = (page: Page) => page.locator(".sd-page .sd-document-card");
const all = (page: Page) =>
  page.getByRole("checkbox", {
    name: "Tout sélectionner sur cette page",
    exact: true,
  });
const count = (page: Page) => page.locator(".sd-pagination > p");
const position = (page: Page) =>
  page.locator(".sd-pagination .sv-page-current");
const next = (page: Page) =>
  page.getByRole("button", { name: "Page suivante", exact: true });
const previous = (page: Page) =>
  page.getByRole("button", { name: "Page précédente", exact: true });
test.use({ viewport: { width: 1600, height: 900 } });
test.beforeEach(async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  (page as Page & { documentErrors: string[] }).documentErrors = errors;
});
test.afterEach(async ({ page }, info) => {
  const errors = (page as Page & { documentErrors: string[] }).documentErrors;
  await info.attach("erreurs-javascript", {
    body: JSON.stringify(errors),
    contentType: "application/json",
  });
  expect(errors).toEqual([]);
});

function document(index: number, animal = "blaireau") {
  return {
    id: `document-${animal}-${index}`,
    title: `Publication enregistrée ${index} — ${animal}`,
    published_date: "2026-10-01",
    url: `https://example.org/publication/${index}`,
    species_links: [{ species: animal }],
    assets: [{ format: ["pdf", "docx", "txt"][index % 3] }],
    status: "indexed",
  };
}
async function fixture(page: Page, total = 50) {
  const documents = [
    ...Array.from({ length: total }, (_, i) => document(i + 1)),
    ...Array.from({ length: 5 }, (_, i) => document(i + 1, "chevreuil")),
  ];
  const calls: { path: string; method: string; offset?: number }[] = [];
  await page.addInitScript(() =>
    localStorage.setItem("symbiose:data-mode:v1", "real"),
  );
  await page.route("**/api/**", async (route) => {
    const request = route.request(),
      url = new URL(request.url()),
      path = url.pathname.replace(/^\/api/, "");
    calls.push({
      path,
      method: request.method(),
      ...(path === "/documents"
        ? { offset: Number(url.searchParams.get("offset")) }
        : {}),
    });
    if (path === "/auth/me")
      return route.fulfill({
        json: {
          user: {
            id: "test-reader",
            display_name: "Lecteur",
            role: "client",
            email: null,
            created_at: "2026-01-01",
            deleted_at: null,
          },
          csrf_token: "test",
        },
      });
    if (path === "/documents") {
      expect(url.searchParams.get("stored_only")).toBe("true");
      const offset = Number(url.searchParams.get("offset")),
        limit = Number(url.searchParams.get("limit"));
      return route.fulfill({ json: documents.slice(offset, offset + limit) });
    }
    if (
      [
        "/console/videos",
        "/console/tasks",
        "/review/samples",
        "/review/species",
        "/parcels/corpora",
      ].includes(path)
    )
      return route.fulfill({ json: [] });
    throw new Error(`Appel inattendu : ${path}`);
  });
  return { documents, calls };
}

test("défaut 16, 17 exemples fictifs, page partielle et préférence indépendante", async ({
  page,
}) => {
  const calls: string[] = [];
  page.on("request", (r) => {
    if (r.url().includes("/api/")) calls.push(r.url());
  });
  await page.addInitScript(() =>
    localStorage.setItem("symbiose:videos-per-page:v1", "8"),
  );
  await page.goto("/documents");
  await expect(size(page)).toHaveValue("16");
  await expect(count(page)).toHaveText("0 document");
  await expect(next(page)).toBeDisabled();
  await expect(previous(page)).toBeDisabled();
  await species(page).selectOption("blaireau");
  await expect(cards(page)).toHaveCount(16);
  await expect(count(page)).toHaveText("1 – 16 sur 17 documents");
  expect(
    (await cards(page).allTextContents()).every((text) =>
      text.includes("Exemple fictif"),
    ),
  ).toBe(true);
  await next(page).click();
  await expect(cards(page)).toHaveCount(1);
  await expect(count(page)).toHaveText("17 – 17 sur 17 documents");
  await expect(next(page)).toBeDisabled();
  await previous(page).click();
  await expect(cards(page)).toHaveCount(16);
  await size(page).selectOption("8");
  await expect(cards(page)).toHaveCount(8);
  await page.reload();
  await expect(size(page)).toHaveValue("8");
  expect(
    await page.evaluate(() =>
      localStorage.getItem("symbiose:videos-per-page:v1"),
    ),
  ).toBe("8");
  await species(page).selectOption("chevreuil");
  await expect(cards(page)).toHaveCount(5);
  await expect(count(page)).toHaveText("1 – 5 sur 5 documents");
  expect(calls).toEqual([]);
});

for (const pageSize of [4, 8, 12, 16])
  test(`50 documents réels, ${pageSize} par page : compteurs, sélection visible et dernière page`, async ({
    page,
  }) => {
    const { calls } = await fixture(page);
    await page.goto("/documents");
    await species(page).selectOption("blaireau");
    await size(page).selectOption(String(pageSize));
    await expect(cards(page)).toHaveCount(pageSize);
    await expect(count(page)).toHaveText(`1 – ${pageSize} sur 50 documents`);
    const pages = Math.ceil(50 / pageSize);
    await expect(position(page)).toHaveText(`Page 1 sur ${pages}`);
    await cards(page).first().getByRole("checkbox").check();
    expect(
      await all(page).evaluate((el) => (el as HTMLInputElement).indeterminate),
    ).toBe(true);
    await all(page).check();
    await expect(page.locator(".sd-selection-count")).toHaveText(
      `${pageSize} sélectionné(s)`,
    );
    await expect(cards(page).locator("input:checked")).toHaveCount(pageSize);
    await all(page).uncheck();
    await expect(cards(page).locator("input:checked")).toHaveCount(0);
    await all(page).check();
    await next(page).click();
    await expect(page.locator(".sd-selection-count")).toHaveText(
      "0 sélectionné(s)",
    );
    await previous(page).click();
    await expect(count(page)).toHaveText(`1 – ${pageSize} sur 50 documents`);
    for (let i = 1; i < pages; i++) await next(page).click();
    const remaining = 50 - (pages - 1) * pageSize;
    await expect(cards(page)).toHaveCount(remaining);
    await expect(count(page)).toHaveText(
      `${50 - remaining + 1} – 50 sur 50 documents`,
    );
    await expect(next(page)).toBeDisabled();
    await expect(
      page.getByRole("button", { name: "Retirer du corpus", exact: true }),
    ).toBeDisabled();
    expect(calls.every((c) => c.method === "GET")).toBe(true);
    expect(calls.filter((c) => c.path === "/documents")).toHaveLength(1);
  });

test("taille et espèce réinitialisent la sélection et la page, en conservant la source et le document consulté", async ({
  page,
}) => {
  const { calls } = await fixture(page);
  await page.goto("/documents");
  await species(page).selectOption("blaireau");
  await next(page).click();
  await all(page).check();
  await size(page).selectOption("4");
  await expect(species(page)).toHaveValue("blaireau");
  await expect(position(page)).toHaveText("Page 1 sur 13");
  await expect(page.locator(".sd-selection-count")).toHaveText(
    "0 sélectionné(s)",
  );
  await all(page).check();
  await species(page).selectOption("chevreuil");
  await expect(cards(page)).toHaveCount(4);
  await expect(page.locator(".sd-selection-count")).toHaveText(
    "0 sélectionné(s)",
  );
  await next(page).click();
  await expect(count(page)).toHaveText("5 – 5 sur 5 documents");
  await cards(page)
    .getByRole("button", {
      name: "Consulter Publication enregistrée 5 — chevreuil",
      exact: true,
    })
    .click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toContainText("Publication enregistrée 5 — chevreuil");
  await expect(
    dialog.getByRole("link", { name: "Consulter la source originale" }),
  ).toHaveAttribute("href", "https://example.org/publication/5");
  await page.keyboard.press("Escape");
  await page.reload();
  await expect(size(page)).toHaveValue("4");
  await selectSource(page, "demo");
  await expect(size(page)).toHaveValue("4");
  await expect(count(page)).toHaveText("0 document");
  await selectSource(page, "real");
  await expect(size(page)).toHaveValue("4");
  expect(calls.every((c) => c.method === "GET")).toBe(true);
});

test("plusieurs centaines de publications : lecture paginée existante, 16 cartes montées et aucun remplissage fictif", async ({
  page,
}) => {
  const { calls } = await fixture(page, 501);
  const start = Date.now();
  await page.goto("/documents");
  await species(page).selectOption("blaireau");
  await expect(cards(page)).toHaveCount(16);
  await expect(count(page)).toHaveText("1 – 16 sur 501 documents");
  await expect(position(page)).toHaveText("Page 1 sur 32");
  expect(
    calls.filter((c) => c.path === "/documents").map((c) => c.offset),
  ).toEqual([0, 200, 400]);
  const loaded = Date.now() - start;
  test.info().annotations.push({
    type: "chargement-fixture-506-documents-ms",
    description: String(loaded),
  });
  await species(page).selectOption("chevreuil");
  await expect(cards(page)).toHaveCount(5);
  expect((await cards(page).allTextContents()).join(" ")).not.toContain(
    "Exemple fictif",
  );
  expect(calls.every((c) => c.method === "GET")).toBe(true);
});

for (const [width, columns] of [
  [1600, 4],
  [1100, 2],
  [768, 2],
  [390, 1],
])
  test(`grille à ${width}px : ${columns} colonnes, cartes homogènes, 16 résultats et défilement naturel`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    await fixture(page, 17);
    await page.goto("/documents");
    await species(page).selectOption("blaireau");
    await expect(cards(page)).toHaveCount(16);
    const rects = await cards(page).evaluateAll((els) =>
      els.map((el) => {
        const r = el.getBoundingClientRect();
        return { x: r.x, y: r.y, height: r.height };
      }),
    );
    expect(new Set(rects.map((r) => r.x)).size).toBe(columns);
    expect(rects.filter((r) => r.y === rects[0].y)).toHaveLength(columns);
    expect(
      new Set(rects.filter((r) => r.y === rects[0].y).map((r) => r.height))
        .size,
    ).toBe(1);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollHeight > innerHeight,
      ),
    ).toBe(true);
    await cards(page).last().getByRole("button").scrollIntoViewIfNeeded();
    await expect(cards(page).last().getByRole("button")).toBeVisible();
  });

test("titres longs, clavier, accessibilité et captures 1600 × 900 à 4, 8 et 16 documents", async ({
  page,
}) => {
  await page.goto("/documents");
  await species(page).selectOption("blaireau");
  await page.evaluate(() => document.fonts.ready);
  const folder = resolve("../output/symbiose/etape-11");
  await mkdir(folder, { recursive: true });
  for (const value of ["4", "8", "16"]) {
    await size(page).selectOption(value);
    await expect(cards(page)).toHaveCount(Number(value));
    await page.evaluate(() => scrollTo(0, 0));
    await page.screenshot({
      path: resolve(folder, `corpus-${value}-1600x900.png`),
    });
    if (value === "16")
      await page.screenshot({
        path: resolve(folder, "corpus-16-complet.png"),
        fullPage: true,
      });
  }
  await size(page).focus();
  await expect(size(page)).toBeFocused();
  await cards(page).first().getByRole("checkbox").focus();
  await page.keyboard.press("Space");
  await expect(cards(page).first()).toHaveClass(/is-selected/);
  const scan = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(
    scan.violations.map((v) => ({
      id: v.id,
      nodes: v.nodes.map((n) => ({
        target: n.target,
        summary: n.failureSummary,
      })),
    })),
  ).toEqual([]);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.evaluate(() => scrollTo(0, 0));
  await page.screenshot({ path: resolve(folder, "corpus-mobile.png") });
});

test("titre intégral non tronqué et hauteurs homogènes malgré un long texte", async ({
  page,
}) => {
  const { documents } = await fixture(page, 17);
  documents[0].title = "Titre long de publication ".repeat(12) + "FIN-DU-TITRE";
  await page.goto("/documents");
  await species(page).selectOption("blaireau");
  const heading = cards(page).first().getByRole("heading");
  await expect(heading).toContainText("FIN-DU-TITRE");
  expect(
    await heading.evaluate((el) => el.scrollHeight <= el.clientHeight),
  ).toBe(true);
  const rows = await cards(page).evaluateAll((els) =>
    els.slice(0, 4).map((el) => el.getBoundingClientRect().height),
  );
  expect(new Set(rows).size).toBe(1);
});

test("administration : présentation en lignes, consultation et sélection conservées", async ({
  page,
}) => {
  await page.route("**/api/auth/me", (route) =>
    route.fulfill({
      json: {
        user: {
          id: "test-admin",
          role: "admin",
          display_name: "Administrateur",
          email: null,
          created_at: "2026-01-01",
          deleted_at: null,
        },
        csrf_token: "test",
      },
    }),
  );
  await page.route("**/api/auth/status", (route) =>
    route.fulfill({ json: { initialized: true, registration_enabled: false } }),
  );
  await page.goto("/admin/documents");
  await page.getByLabel("Espèce", { exact: true }).selectOption("chevreuil");
  const entries = page.locator(".adm-content .sd-document-card");
  await expect(entries).toHaveCount(5);
  expect(
    await entries.first().evaluate((el) => getComputedStyle(el).flexDirection),
  ).toBe("row");
  expect(
    await page
      .locator(".adm-content .sd-document-list")
      .evaluate(
        (el) => getComputedStyle(el).gridTemplateColumns.split(" ").length,
      ),
  ).toBe(1);
  await entries.first().getByRole("checkbox").check();
  await expect(entries.first()).toHaveClass(/is-selected/);
  await entries
    .first()
    .getByRole("button", { name: /Lire le document/ })
    .click();
  await expect(page.getByRole("dialog")).toContainText("EXEMPLE FICTIF");
  await page.keyboard.press("Escape");
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({
    path: resolve(
      "../output/symbiose/etape-11/administration-documents-1600x900.png",
    ),
  });
});
