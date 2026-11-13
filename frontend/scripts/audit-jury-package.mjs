import { chromium } from "@playwright/test";
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const base = process.env.JURY_PACKAGE_URL || "http://127.0.0.1:8088";
const output = path.resolve("../output/symbiose/final/package");
await mkdir(output, { recursive: true });
const browser = await chromium.launch();
const errors = [],
  requests = [];
try {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
  });
  const page = await context.newPage();
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("request", (r) => requests.push(r.url()));
  await page.goto(`${base}/jury/?render=2d`);
  await page.locator(".sx-stage--ready").waitFor();
  assert.equal(await page.locator(".sx-canvas").count(), 0);
  await page.getByRole("button", { name: "Plein écran", exact: true }).click();
  await page.waitForFunction(() => !!document.fullscreenElement);
  const fullscreen = await page.evaluate(() => !!document.fullscreenElement);
  await page.evaluate(() => document.exitFullscreen());
  await page.waitForFunction(() => !document.fullscreenElement);
  await page.setViewportSize({ width: 1024, height: 768 });
  await page.getByText("Préparation du jury", { exact: false }).click();
  await page
    .getByRole("button", { name: "Installer hors ligne", exact: true })
    .click();
  await page
    .locator(".jury-installation [role=status]")
    .filter({ hasText: "Installation locale prête" })
    .waitFor({ timeout: 60000 });
  const installation = await page
    .locator(".jury-installation [role=status]")
    .innerText();
  await page.getByText("Préparation du jury", { exact: false }).click();
  await context.setOffline(true);
  await page.reload();
  await page.locator(".sx-stage--ready").waitFor();
  await page.setViewportSize({ width: 1440, height: 900 });
  const chapters = [];
  const ids = [
    "forest",
    "sky",
    "rivers",
    "underwater",
    "wetland",
    "meadow",
    "coast",
    "night-forest",
  ];
  for (let i = 0; i < 8; i++) {
    await page.locator(".sx-chapter-nav button").nth(i).click();
    await page.waitForFunction(
      (id) =>
        document.querySelector(".sx-pitch-content")?.dataset.chapter === id,
      ids[i],
    );
    await page.waitForFunction(() =>
      [...document.querySelectorAll(".sx-fallback-scene img")].every(
        (image) => image.complete && image.naturalWidth > 0,
      ),
    );
    await page
      .locator(".sx-fallback-scene img")
      .evaluateAll((images) =>
        Promise.all(images.map((image) => image.decode())),
      );
    chapters.push(
      await page.locator(".sx-pitch-content").getAttribute("data-chapter"),
    );
    await page.locator(".sx-demo img").evaluateAll(images => Promise.all(images.map(image => image.decode())));
    await page.screenshot({ path: path.join(output, `${String(i + 1).padStart(2, "0")}-${ids[i]}.png`) });
  }
  assert.equal(new Set(chapters).size, 8);
  await page.getByRole("button", { name: "Le projet", exact: true }).click();
  await page.getByRole("dialog").waitFor();
  assert.ok((await page.getByRole("dialog").innerText()).includes("Normandie"));
  await page.keyboard.press("Escape");
  const link = page.getByRole("link", {
    name: "Commencer l’expérience Symbiose",
  });
  const href = await link.getAttribute("href");
  assert.equal(href, "http://localhost:8080/connexion");
  await page.screenshot({
    path: path.join(output, "portable-offline-final.png"),
  });
  const juryRequests = [...requests];
  assert.ok(!juryRequests.some((url) => url.includes("/api/")));
  assert.ok(
    juryRequests.every((url) =>
      ["127.0.0.1", "localhost"].includes(new URL(url).hostname),
    ),
  );
  await context.setOffline(false);
  await link.click();
  await page.waitForURL("**/connexion");
  await page
    .getByRole("button", { name: "Se connecter", exact: true })
    .waitFor();
  const result = {
    date: new Date().toISOString(),
    browser: browser.version(),
    base,
    fullscreen,
    fullscreenExit: true,
    resize: "1024x768",
    installation,
    offlineReload: true,
    chapters,
    offlineSources: true,
    applicationHref: href,
    applicationReached: page.url(),
    apiCallsInJury: 0,
    externalCallsInJury: 0,
    errors,
  };
  assert.deepEqual(errors, []);
  await writeFile(
    path.join(output, "report.json"),
    JSON.stringify(result, null, 2),
  );
  console.log(JSON.stringify(result, null, 2));
} finally {
  await browser.close();
}
