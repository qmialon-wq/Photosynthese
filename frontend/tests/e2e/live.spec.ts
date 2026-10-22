import { test, expect } from "@playwright/test";
import { readFile } from "node:fs/promises";
test("vidéo réelle : transfert navigateur, inférence worker, MP4 lisible et rapport", async ({
  page,
}, info) => {
  test.skip(
    !process.env.BIOSENTINELLE_LIVE_VIDEO,
    "Fournir explicitement une vidéo de test locale et démarrer Compose ML.",
  );
  test.setTimeout(180000);
  await page.addInitScript(() =>
    localStorage.setItem("biosentinelle-reviewer", "diagnostic-navigateur"),
  );
  await page.goto("/videos");
  await page
    .getByLabel("Importer une vidéo", { exact: true })
    .setInputFiles(process.env.BIOSENTINELLE_LIVE_VIDEO!);
  await expect(
    page.getByRole("heading", { name: "Configurer l’analyse" }),
  ).toBeVisible({ timeout: 60000 });
  await page.getByLabel("Analyser une image sur").fill("10");
  if (process.env.BIOSENTINELLE_LIVE_CLASSIFY === "1")
    await page.getByLabel("Détection seule, sans classification").uncheck();
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
