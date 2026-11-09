import { chromium } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

const phase = process.argv[2] || "final";
const destination = resolve("../output/symbiose/etape-7", phase);
await mkdir(destination, { recursive: true });
const sections = [
  ["accueil", "/"],
  ["videotheque", "/videos"],
  ["mes-dossiers", "/parcelles"],
  ["analyses", "/analyses"],
  ["validation-humaine", "/review"],
  ["documents-scientifiques", "/documents"],
];
const sizes =
  phase === "avant"
    ? [[1600, 900]]
    : [
        [1920, 1080],
        [1600, 900],
        [1440, 900],
        [1280, 800],
        [390, 844],
      ];
const browser = await chromium.launch();
const report = [];
try {
  const page = await browser.newPage({ reducedMotion: "reduce" });
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("response", (response) => {
    if (response.status() >= 400)
      errors.push(`${response.status()} ${response.url()}`);
  });
  for (const [width, height] of sizes) {
    await page.setViewportSize({ width, height });
    for (const [name, path] of sections) {
      errors.length = 0;
      await page.goto(`http://127.0.0.1:4173${path}`);
      await page.locator(".sym-wheel-link.is-active").waitFor();
      await page.evaluate(async () => {
        await document.fonts.ready;
        await Promise.all(
          [...document.images].map((image) => image.decode().catch(() => {})),
        );
        await Promise.all(
          [
            ...document.querySelectorAll(
              ".sym-forest,.sym-photo,.sf-project-photo,.sa-poster,.sr-observation-photo",
            ),
          ].map(async (el) => {
            const url = getComputedStyle(el).backgroundImage.match(
              /url\(["']?(.*?)["']?\)/,
            )?.[1];
            if (!url) return;
            const image = new Image();
            image.src = url;
            await image.decode();
          }),
        );
      });
      await page.waitForFunction(() =>
        [...document.querySelectorAll(".sr-observation-preview video")].every(
          (video) => video.readyState >= 2 && !video.seeking,
        ),
      );
      const measurements = await page.evaluate(() => {
        const box = (selector) => {
          const element = document.querySelector(selector);
          const { x, y, width, height } = element.getBoundingClientRect();
          return { x, y, width, height };
        };
        const clipped = [
          ...document.querySelectorAll(
            "h1, h2, h3, button, select, .sym-stat p, .sym-wheel-link.is-active .sym-wheel-label",
          ),
        ]
          .filter(
            (el) =>
              !el.classList.contains("sym-sr-only") &&
              el.clientWidth > 0 &&
              el.scrollWidth > el.clientWidth + 2,
          )
          .map((el) => ({
            selector: el.className,
            text: el.textContent?.trim(),
            width: el.clientWidth,
            scroll: el.scrollWidth,
          }));
        return {
          horizontalOverflow: document.documentElement.scrollWidth > innerWidth,
          clipped,
          shell: Object.fromEntries(
            [
              ".sym-brand",
              ".sym-header-actions",
              ".sym-wheel",
              ".sym-wheel-arc",
              ".sym-settings",
              ".sym-forest",
              ".sym-main",
              ".sym-wheel-link.is-active",
            ].map((selector) => [selector, box(selector)]),
          ),
        };
      });
      const filename = `${name}-${width}x${height}.png`;
      await page.screenshot({ path: resolve(destination, filename) });
      report.push({
        name,
        path,
        width,
        height,
        filename,
        ...measurements,
        errors: [...errors],
      });
      console.log(
        `${filename}: overflow=${measurements.horizontalOverflow}, clipped=${measurements.clipped.length}, errors=${errors.length}`,
      );
    }
  }
  if (phase !== "avant") {
    await page.route("**/api/**", (route) => {
      const path = new URL(route.request().url()).pathname;
      return path === "/api/auth/me"
        ? route.fulfill({ status: 401, json: { detail: "Connexion requise" } })
        : route.fulfill({ json: { setup_required: false } });
    });
    for (const [width, height] of [
      [1600, 900],
      [390, 844],
    ]) {
      await page.setViewportSize({ width, height });
      await page.goto("http://127.0.0.1:4173/connexion");
      await page
        .getByRole("heading", { name: "Connexion", exact: true })
        .waitFor();
      await page.screenshot({
        path: resolve(destination, `connexion-${width}x${height}.png`),
      });
    }
  }
  await writeFile(
    resolve(destination, "verification.json"),
    JSON.stringify(report, null, 2),
  );
  await writeFile(
    resolve(destination, "index.html"),
    `<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Symbiose — captures ${phase}</title><style>body{font:16px system-ui;background:#073322;color:#f5f8ef;margin:24px}nav{display:flex;gap:16px;flex-wrap:wrap}a{color:#b9ef84}img{max-width:100%;height:auto;border:1px solid #728d68}figure{margin:32px 0}figcaption{margin:8px 0}</style><h1>Symbiose — audit graphique : ${phase}</h1><nav>${sizes.map(([w, h]) => `<a href="#taille-${w}">${w} × ${h}</a>`).join("")}</nav>${sizes
      .map(
        ([w, h]) =>
          `<h2 id="taille-${w}">${w} × ${h}</h2>${report
            .filter((r) => r.width === w)
            .map(
              (r) =>
                `<figure><figcaption>${r.name}</figcaption><a href="${r.filename}"><img loading="lazy" src="${r.filename}" alt="${r.name} à ${w} × ${h}"></a></figure>`,
            )
            .join("")}`,
      )
      .join("")}</html>`,
  );
} finally {
  await browser.close();
}
