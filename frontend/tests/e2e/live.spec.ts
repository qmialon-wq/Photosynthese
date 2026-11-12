import { test, expect } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { loginLive } from "./live-auth";
test("vidéo réelle : transfert navigateur, inférence worker, MP4 lisible et rapport", async ({
  page,
}, info) => {
  test.skip(
    !process.env.BIOSENTINELLE_LIVE_VIDEO,
    "Fournir explicitement une vidéo de test locale et démarrer Compose ML.",
  );
  test.setTimeout(180000);
  await loginLive(page);
  await page.goto("/videos");
  await page
    .getByRole("button", { name: "Importer des vidéos", exact: true })
    .click();
  await page
    .getByLabel("Sélectionner des fichiers vidéo", { exact: true })
    .setInputFiles(process.env.BIOSENTINELLE_LIVE_VIDEO!);
  await page
    .getByRole("button", { name: "Envoyer les vidéos", exact: true })
    .click();
  await expect(
    page.getByText("Import terminé, vidéo sélectionnée", { exact: false }),
  ).toBeVisible({ timeout: 60000 });
  await page
    .getByRole("button", { name: "Fermer la fenêtre", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Prévisualiser", exact: true })
    .first()
    .click();
  await page
    .getByRole("link", { name: "Analyser cette vidéo", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Configurer l’analyse" }),
  ).toBeVisible({ timeout: 60000 });
  await page.getByLabel("Recevoir mon dossier biodiversité").uncheck();
  await page.getByLabel("Niveau de détail").selectOption("fast");
  if (process.env.BIOSENTINELLE_LIVE_CLASSIFY === "1")
    await page.getByLabel("Objectif de l'analyse").selectOption("false");
  await page
    .getByRole("button", { name: "Lancer l’analyse", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Vidéo annotée" }),
  ).toBeVisible({ timeout: 120000 });
  const video = page.locator("video").last();
  await expect
    .poll(
      () =>
        video.evaluate((element) => (element as HTMLVideoElement).videoWidth),
      { timeout: 15000 },
    )
    .toBeGreaterThan(0);
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("link", { name: /Rapport JSON/ }).click();
  const download = await downloadPromise;
  const filename = info.outputPath("report.json");
  await download.saveAs(filename);
  const report = JSON.parse(await readFile(filename, "utf8"));
  expect(report.frames_decoded).toBeGreaterThan(0);
  expect(report.detector_identity).toContain("megadetector:md_v5a");
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Vidéo annotée" }),
  ).toBeVisible({ timeout: 15000 });
});
