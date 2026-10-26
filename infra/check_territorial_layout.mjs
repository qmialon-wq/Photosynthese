// Check the real printable stylesheet in Chromium, including footer collisions.
import { chromium } from "../frontend/node_modules/playwright-core/index.mjs";
import { pathToFileURL } from "node:url";

const [htmlPath, pdfPath] = process.argv.slice(2);
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage();
  await page.goto(pathToFileURL(htmlPath).href);
  await page.emulateMedia({ media: "print" });
  const layout = await page.locator(".page").evaluateAll((pages) =>
    pages.map((section) => ({
      paragraphsBottom: Math.max(...Array.from(section.querySelectorAll("p")).map((p) => p.getBoundingClientRect().bottom)),
      footerTop: section.querySelector("footer").getBoundingClientRect().top,
      height: section.getBoundingClientRect().height,
    })),
  );
  if (layout.length !== 4 || layout.some((p) => p.paragraphsBottom >= p.footerTop)) {
    throw new Error(`Printable page overflow: ${JSON.stringify(layout)}`);
  }
  await page.pdf({ path: pdfPath, preferCSSPageSize: true, printBackground: true });
  console.log(JSON.stringify({ pages: layout.length, overlap: false, pdf: pdfPath }));
} finally {
  await browser.close();
}
