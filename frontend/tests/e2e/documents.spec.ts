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
  content += "%" + "x".repeat(6 * 1024 * 1024) + "\n";
  const xref = content.length;
  content += "xref\n0 6\n0000000000 65535 f \n";
  content += offsets
    .map((offset) => `${String(offset).padStart(10, "0")} 00000 n \n`)
    .join("");
  return Buffer.from(
    content + `trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`,
  );
}

test("collecte globale/ciblée, français, retrait multiple persistant par espèce et mobile", async ({
  page,
}) => {
  const excluded = new Set<string>();
  const collected: string[][] = [];
  function doc(id: string) {
    return {
      id,
      title: `Road wildlife ${id}`,
      authors: [],
      language: "en",
      status: "indexed",
      species_links: [],
      assets: [],
      metadata: {
        translation_fr: {
          status: "completed",
          source_title: `Road wildlife ${id}`,
          title: `Routes et animaux ${id}`,
        },
      },
    };
  }
  await page.route("**/api/**", (route) => {
    const url = new URL(route.request().url()),
      path = url.pathname;
    if (path === "/api/documents/collect") {
      collected.push(route.request().postDataJSON().species);
      return route.fulfill({ json: { tasks: [] } });
    }
    if (path === "/api/documents/remove") {
      const body = route.request().postDataJSON();
      body.documents.forEach((id: string) =>
        excluded.add(body.species + ":" + id),
      );
      return route.fulfill({ json: { removed: body.documents } });
    }
    let result: unknown = [];
    if (path === "/api/documents/species")
      result = [
        { name: "renards", display_name: "Renard", documents_count: 2 },
        { name: "blaireaux", display_name: "Blaireau", documents_count: 2 },
      ];
    else if (path === "/api/documents") {
      expect(url.searchParams.get("stored_only")).toBe("true");
      result = ["first", "second"]
        .filter(
          (id) => !excluded.has(url.searchParams.get("species") + ":" + id),
        )
        .map(doc);
    } else if (path.endsWith("/first/pages"))
      result = [
        {
          asset_id: "file",
          page_number: 1,
          clean_text: "English original content.",
          translated_text: "Texte traduit en français.",
          references_data: [],
        },
      ];
    else if (path.endsWith("/first")) result = doc("first");
    return route.fulfill({ json: result });
  });
  await page.goto("/documents");
  await page
    .getByRole("button", {
      name: "Récupérer pour toutes les espèces",
      exact: true,
    })
    .click();
  expect(collected).toEqual([[]]);
  await page
    .getByRole("button", { name: "Choisir les espèces", exact: true })
    .click();
  await page
    .getByRole("group", { name: "Espèces à rechercher" })
    .getByLabel("Blaireau", { exact: true })
    .check();
  await page
    .getByRole("button", {
      name: "Récupérer les documents des espèces choisies",
      exact: true,
    })
    .click();
  expect(collected[1]).toEqual(["renards", "blaireaux"]);
  await page
    .getByRole("article")
    .first()
    .getByRole("button", { name: "Lire le document", exact: true })
    .click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.locator("pre")).toHaveText("Texte traduit en français.");
  await dialog.getByRole("button", { name: "Original", exact: true }).click();
  await expect(dialog.locator("pre")).toHaveText("English original content.");
  await page.reload();
  await page.getByLabel("Tout sélectionner sur cette page").check();
  await page
    .getByRole("button", { name: "Retirer du corpus", exact: true })
    .click();
  await expect(page.getByRole("article")).toHaveCount(0);
  await page.reload();
  await expect(page.getByRole("article")).toHaveCount(0);
  await page.getByLabel("Espèce", { exact: true }).selectOption("blaireaux");
  await expect(page.getByRole("article")).toHaveCount(2);
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
  await page.setViewportSize({ width: 390, height: 844 });
  await page
    .getByRole("button", { name: "Choisir les espèces", exact: true })
    .click();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});

test("PDF réel importé, traduit localement et retiré depuis le navigateur", async ({
  page,
}) => {
  test.skip(
    process.env.BIOSENTINELLE_DOCUMENTS_E2E !== "1",
    "Activer le diagnostic réel Docker",
  );
  test.setTimeout(90000);
  const identity = `fixture-${Date.now()}`;
  await page.addInitScript(() =>
    localStorage.setItem("biosentinelle-reviewer", "diagnostic-documents"),
  );
  let documentId: string | undefined;
  try {
    await page.goto("/documents");
    await page
      .getByRole("button", { name: "Importer un document", exact: true })
      .click();
    await page
      .getByLabel(/Fichier PDF, TXT/)
      .setInputFiles({
        name: identity + ".pdf",
        mimeType: "application/pdf",
        buffer: pdfFixture(identity),
      });
    await page.getByLabel(/Je dispose du droit/).check();
    const uploaded = page.waitForResponse(
      (r) =>
        r.url().includes("/documents/upload") &&
        r.request().method() === "POST",
    );
    await page
      .getByRole("button", { name: "Importer le document", exact: true })
      .click();
    const task = await (await uploaded).json();
    await expect
      .poll(
        async () => {
          const job = await (
            await page.request.get(`/api/documents/tasks/${task.id}`)
          ).json();
          documentId = job.result?.document_id;
          return job.status;
        },
        { timeout: 35000 },
      )
      .toBe("completed");
    const card = page.locator(`article[data-document-id="${documentId}"]`);
    await expect(card).toBeVisible({ timeout: 15000 });
    await expect(
      card.getByText("Traduit en français", { exact: true }),
    ).toBeVisible({ timeout: 35000 });
    await card
      .getByRole("button", { name: "Lire le document", exact: true })
      .click();
    const dialog = page.getByRole("dialog");
    await expect(dialog.locator("pre")).toContainText(
      /publication scientifique/i,
    );
    await dialog.getByRole("button", { name: "Original", exact: true }).click();
    await expect(dialog.locator("pre")).toContainText("Synthetic fixture");
    await page.reload();
    await card.getByRole("checkbox").check();
    await page
      .getByRole("button", { name: "Retirer du corpus", exact: true })
      .click();
    await expect(card).toHaveCount(0);
    await page.reload();
    await expect(card).toHaveCount(0);
  } finally {
    if (documentId) {
      await page.request.post("/api/documents/remove", {
        data: { species: "renards", documents: [documentId] },
        headers: { "X-Reviewer": "diagnostic-documents" },
      });
      await page.request.post(`/api/documents/${documentId}/review`, {
        data: {
          relevance: "rejected",
          quality: "rejected",
          note: "Fixture synthétique de test navigateur, hors corpus scientifique.",
        },
        headers: { "X-Reviewer": "diagnostic-documents" },
      });
    }
  }
});
