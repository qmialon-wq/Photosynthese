import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

function pdfFixture(identity: string): Buffer {
  const text = `BT /F1 12 Tf 30 740 Td (Synthetic fixture ${identity} for automated tests only. Not a scientific publication.) Tj ET`;
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    `<< /Length ${text.length} >>\nstream\n${text}\nendstream`,
  ];
  let content = "%PDF-1.4\n";
  const offsets: number[] = [];
  objects.forEach((object, index) => {
    offsets.push(content.length);
    content += `${index + 1} 0 obj\n${object}\nendobj\n`;
  });
  // Dépasse l'ancienne limite Nginx de 5 Mio sans changer le texte extrait.
  content += "%" + "x".repeat(6 * 1024 * 1024) + "\n";
  const xref = content.length;
  content += "xref\n0 6\n0000000000 65535 f \n";
  content += offsets
    .map((offset) => `${String(offset).padStart(10, "0")} 00000 n \n`)
    .join("");
  content += `trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return Buffer.from(content);
}

test("recherche, consultation et sélection persistante par espèce", async ({
  page,
}) => {
  let selected = false;
  let searches = 0;
  const doc = () => ({
    id: "fixture",
    title: "Publication de test sur le renard",
    authors: ["Auteur de test"],
    abstract: "Résumé synthétique de fixture",
    status: "indexed",
    published_date: "2026",
    url: null,
    species_links: [
      { species: "renards", enabled: selected, available: selected },
    ],
    assets: [],
    provenance: [],
    selection_history: [],
  });
  await page.route("**/api/**", (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    if (
      path.endsWith("/species/renards") &&
      route.request().method() === "PUT"
    ) {
      selected = route.request().postDataJSON().enabled;
      return route.fulfill({ json: {} });
    }
    if (path === "/api/documents/search") {
      expect(route.request().postDataJSON().species).toEqual(["Vulpes vulpes"]);
      searches++;
      return route.fulfill({ json: { id: "job" } });
    }
    const result =
      path === "/api/documents/search-profiles"
        ? {
            version: "test",
            activities: [
              { value: "all", label: "Tous les aménagements" },
              { value: "transport", label: "Routes et transports" },
            ],
          }
        : path === "/api/documents/species"
          ? [
              {
                name: "renards",
                scientific_name: "Vulpes vulpes",
                display_name: "Renard",
                documents_count: 1,
                selected_count: Number(selected),
              },
            ]
          : path === "/api/documents/fixture"
            ? doc()
            : path.includes("/fixture/pages")
              ? [
                  {
                    asset_id: "fixture",
                    page_number: 1,
                    clean_text: "Texte intégral de fixture.",
                    language: "fr",
                    references_data: [],
                  },
                ]
              : path === "/api/documents"
                ? url.searchParams.get("selected_only") === "true" && !selected
                  ? []
                  : [doc()]
                : path === "/api/documents/tasks/job"
                  ? { id: "job", status: "completed" }
                  : [];
    return route.fulfill({ json: result });
  });
  await page.goto("/documents");
  await expect(
    page.getByRole("heading", { name: "Documents scientifiques", exact: true }),
  ).toBeVisible();
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
  await page
    .getByRole("button", { name: "Rechercher des publications", exact: true })
    .click();
  await page.getByRole("button", { name: "Lancer la recherche" }).click();
  await expect(page.getByText(/Recherche lancée/)).toBeVisible();
  expect(searches).toBe(1);
  await page.getByRole("button", { name: "Consulter", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByText("Texte intégral de fixture.")).toBeVisible();
  await dialog
    .getByRole("button", { name: "Valider et ajouter aux sources" })
    .click();
  await expect(
    dialog.getByRole("button", { name: "Retirer des sources" }),
  ).toBeVisible();
  await page.reload();
  await page.getByLabel("Filtrer par espèce").selectOption("renards");
  await page.getByLabel("Sources sélectionnées uniquement").check();
  await expect(
    page.getByRole("button", { name: "Retirer des sources" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Retirer des sources" }).click();
  await expect(page.getByText(/Aucun document pour ces filtres/)).toBeVisible();
  await page.reload();
  await expect(
    page.getByText("Source sélectionnée", { exact: true }),
  ).toHaveCount(0);
  await page.setViewportSize({ width: 390, height: 844 });
  await page
    .getByRole("button", { name: "Rechercher des publications", exact: true })
    .click();
  await expect(page.getByLabel("Objectif de la recherche")).toHaveValue(
    "human_activities",
  );
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});

test("import réel via le web, indexation et retrait après rechargement", async ({
  page,
}) => {
  test.skip(
    process.env.BIOSENTINELLE_DOCUMENTS_E2E !== "1",
    "Diagnostic explicite sur le backend et worker locaux",
  );
  const title = `Fixture documentaire E2E ${Date.now()}`;
  await page.addInitScript(() =>
    localStorage.setItem("biosentinelle-reviewer", "diagnostic-documents"),
  );
  let documentId: string | undefined;
  try {
    await page.goto("/documents");
    await page
      .getByRole("button", { name: "Importer un document", exact: true })
      .click();
    await page.getByLabel("Espèce du document").selectOption("renards");
    await page.getByLabel("Titre (facultatif)", { exact: true }).fill(title);
    await page.getByLabel(/Fichier PDF, TXT/).setInputFiles({
      name: "fixture-web.pdf",
      mimeType: "application/pdf",
      buffer: pdfFixture(title),
    });
    await page.getByLabel(/Je dispose du droit/).check();
    const uploaded = page.waitForResponse(
      (response) =>
        response.url().includes("/documents/upload") &&
        response.request().method() === "POST",
    );
    await page
      .getByRole("button", { name: "Importer et extraire le texte" })
      .click();
    const task = await (await uploaded).json();
    await page.getByLabel("Filtrer par espèce").selectOption("renards");
    const card = page.getByRole("article").filter({ hasText: title });
    await expect(card).toBeVisible({ timeout: 25000 });
    documentId = (
      await (await page.request.get(`/api/documents/tasks/${task.id}`)).json()
    ).result.document_id;
    await card.getByRole("button", { name: "Consulter", exact: true }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog.locator("pre")).toContainText("Synthetic fixture");
    await dialog
      .getByRole("button", { name: "Valider et ajouter aux sources" })
      .click();
    await expect(
      dialog.getByRole("button", { name: "Retirer des sources" }),
    ).toBeVisible();
    await page.reload();
    await page.getByLabel("Filtrer par espèce").selectOption("renards");
    await card.getByRole("button", { name: "Retirer des sources" }).click();
    await page.reload();
    await page.getByLabel("Filtrer par espèce").selectOption("renards");
    await expect(
      card.getByRole("button", { name: "Valider et ajouter", exact: true }),
    ).toBeVisible();
  } finally {
    if (documentId) {
      await page.request.put(`/api/documents/${documentId}/species/renards`, {
        data: { enabled: false },
        headers: { "X-Reviewer": "diagnostic-documents" },
      });
      await page.request.post(`/api/documents/${documentId}/review`, {
        data: {
          relevance: "rejected",
          quality: "rejected",
          note: "Fixture synthétique de test navigateur, exclue des sources écologiques.",
        },
        headers: { "X-Reviewer": "diagnostic-documents" },
      });
    }
  }
});
