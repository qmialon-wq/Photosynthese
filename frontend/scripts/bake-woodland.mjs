import { execFileSync } from "node:child_process";
import { chromium } from "@playwright/test";
import { writeFile, mkdir, unlink } from "node:fs/promises";
execFileSync("python", ["scripts/prepare-scenery-assets.py", "--stage-tree"], {
  stdio: "inherit",
});
const browser = await chromium.launch({
  args: process.platform === "win32" ? ["--use-angle=d3d11"] : [],
});
try {
  const page = await browser.newPage();
  await page.goto(
    (process.env.E2E_BASE_URL || "http://127.0.0.1:4173") +
      "/tools/bake-woodland.html",
  );
  await page.waitForFunction(() => window.done, {}, { timeout: 60000 });
  const images = await page.evaluate(() => window.baked);
  await mkdir("../output/symbiose/scenery-sources/tree-atlas", {
    recursive: true,
  });
  for (let i = 0; i < images.length; i++)
    await writeFile(
      `../output/symbiose/scenery-sources/tree-atlas/${i}.png`,
      Buffer.from(images[i].split(",")[1], "base64"),
    );
} finally {
  await browser.close();
  await unlink("tools/tree-source.glb");
}
