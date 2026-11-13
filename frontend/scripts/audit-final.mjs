import { chromium } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
const phase = process.argv.includes("--baseline")
  ? "baseline"
  : process.argv.includes("--review")
    ? "review"
    : "final";
const fallback = process.argv.includes("--fallback");
const gpu = process.argv.includes("--gpu");
const jury = process.argv.includes("--jury");
const base = process.env.E2E_BASE_URL || "http://127.0.0.1:8080";
const output = path.resolve(
  `../output/symbiose/final/${phase}-${fallback ? "2d" : gpu ? "gpu" : "software"}`,
);
await mkdir(output, { recursive: true });
const browser = await chromium.launch(
  gpu && process.platform === "win32"
    ? { args: ["--use-angle=d3d11", "--ignore-gpu-blocklist"] }
    : !gpu && !fallback
      ? { args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] }
      : {},
);
const anchors = [0, 35, 60, 95, 115, 150, 180, 210];
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
const errors = [],
  external = [];
try {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 900 },
  });
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (!["localhost", "127.0.0.1"].includes(url.hostname))
      external.push(url.href);
  });
  if (!jury)
    await page.route("**/api/**", (route) =>
      route.fulfill({ status: 401, json: { detail: "public audit fixture" } }),
    );
  if (fallback)
    await page.addInitScript(() => {
      const original = HTMLCanvasElement.prototype.getContext;
      HTMLCanvasElement.prototype.getContext = function (type, ...args) {
        return type === "webgl2" ? null : original.call(this, type, ...args);
      };
    });
  const start = Date.now();
  await page.goto(
    `${base}${jury ? "/jury/" : "/"}${!gpu && !fallback ? "?render=software" : ""}`,
  );
  await page.locator(".sx-stage--ready").waitFor({ timeout: 45000 });
  await page
    .locator(".sx-progress input")
    .evaluate((input) => (input.step = "any"));
  const startupMs = Date.now() - start;
  const frames = () =>
    page
      .locator(".sx-canvas")
      .evaluateAll((elements) =>
        elements[0]?.dataset.state
          ? JSON.parse(elements[0].dataset.state)
          : null,
      );
  async function seek(progress) {
    await page
      .getByRole("slider", { name: "Position dans le récit" })
      .evaluate((input, p) => {
        input.value = String(p * 100);
        input.dispatchEvent(new Event("input", { bubbles: true }));
      }, progress);
    await page
      .waitForFunction(
        (p) =>
          Math.abs(
            Number(document.querySelector(".sx-experience").dataset.progress) -
              p,
          ) < 0.00001,
        progress,
        { timeout: 10000 },
      )
      .catch(async (error) => {
        console.error(
          await page.evaluate(
            (p) => ({
              expected: p,
              actual: document.querySelector(".sx-experience").dataset.progress,
              slider: document.querySelector(".sx-progress input").value,
              scroll: scrollY,
            }),
            progress,
          ),
        );
        throw error;
      });
    await page.waitForFunction(() => {
      const state = document.querySelector(".sx-canvas")?.dataset.state;
      return !state || !JSON.parse(state).assetsPending;
    });
    await page.evaluate(async () => {
      let last = "",
        stable = 0;
      await new Promise((resolve) => {
        function tick() {
          const current =
            document.querySelector(".sx-canvas")?.dataset.state ??
            document.querySelector(".sx-experience").dataset.progress;
          stable = current === last ? stable + 1 : 0;
          last = current;
          stable >= 4 ? resolve() : requestAnimationFrame(tick);
        }
        requestAnimationFrame(tick);
      });
    });
    await page
      .locator(".sx-fallback-scene img")
      .evaluateAll((images) =>
        Promise.all(images.map((image) => image.decode())),
      );
    await page
      .locator(".sx-demo img")
      .evaluateAll((images) =>
        Promise.all(images.map((image) => image.decode())),
      );
  }
  const scenes = [];
  for (let i = 0; i < 8; i++) {
    await seek(anchors[i] / 210);
    await page
      .locator(`.sx-pitch-content[data-chapter="${ids[i]}"] .sx-pitch-scene`)
      .waitFor();
    const screenshot = `${String(i + 1).padStart(2, "0")}-${ids[i]}.png`;
    await page.screenshot({ path: path.join(output, screenshot) });
    scenes.push({ id: ids[i], screenshot, state: await frames() });
  }
  const measurements = [];
  if (!fallback && phase !== "review") {
    for (let i = 0; i < 7; i++) {
      await seek(anchors[i] / 210);
      const measurement = await page.evaluate(
        async ({ from, to }) => {
          const slider = document.querySelector(".sx-progress input");
          const canvas = document.querySelector(".sx-canvas");
          const intervals = [],
            renderedIntervals = [];
          let previous = 0,
            lastRender = 0,
            lastCount = Number(canvas.dataset.renderCount),
            totalRenders = 0,
            samples = 0;
          const began = performance.now();
          await new Promise((resolve) => {
            function tick(now) {
              const elapsed = now - began,
                t = Math.min(1, elapsed / 3500),
                p = t < 0.5 ? t * 2 : 2 - t * 2;
              const count = Number(canvas.dataset.renderCount);
              if (elapsed > 700 && previous) {
                intervals.push(now - previous);
                samples++;
                totalRenders += Math.max(0, count - lastCount);
                if (count > lastCount) {
                  if (lastRender) renderedIntervals.push(now - lastRender);
                  lastRender = now;
                }
              }
              lastCount = count;
              previous = now;
              slider.value = String(((from + (to - from) * p) / 210) * 100);
              slider.dispatchEvent(new Event("input", { bubbles: true }));
              t < 1 ? requestAnimationFrame(tick) : resolve();
            }
            requestAnimationFrame(tick);
          });
          const stats = (values) => {
            const sorted = [...values].sort((a, b) => a - b),
              sum = values.reduce((a, b) => a + b, 0);
            return {
              samples: values.length,
              fps: (values.length * 1000) / sum,
              p95Ms: sorted[Math.floor(sorted.length * 0.95)],
              worstMs: sorted.at(-1),
            };
          };
          return {
            raf: stats(intervals),
            rendered: stats(renderedIntervals),
            totalRenders,
            samples,
            finalState: JSON.parse(canvas.dataset.state),
          };
        },
        { from: anchors[i], to: anchors[i + 1] },
      );
      measurements.push({
        transition: `${ids[i]} → ${ids[i + 1]}`,
        ...measurement,
      });
    }
  }
  await seek(0);
  const beforeIdle = await frames();
  await page.waitForTimeout(2200); // Measurement window, never an animation clock.
  const afterIdle = await frames();
  const transfer = await page.evaluate(() => ({
    requests: performance.getEntriesByType("resource").length,
    bytes: performance
      .getEntriesByType("resource")
      .reduce((sum, e) => sum + e.transferSize, 0),
    jsHeapBytes: performance.memory?.usedJSHeapSize ?? null,
  }));
  const report = {
    date: new Date().toISOString(),
    phase,
    base,
    jury,
    fallback,
    browser: browser.version(),
    os: `${os.type()} ${os.release()}`,
    cpu: os.cpus()[0].model,
    ramBytes: os.totalmem(),
    startupMs,
    scenes,
    measurements,
    idleRenderDelta:
      beforeIdle && afterIdle
        ? afterIdle.renderCount - beforeIdle.renderCount
        : null,
    transfer,
    errors,
    external,
  };
  await writeFile(
    path.join(output, "report.json"),
    JSON.stringify(report, null, 2) + "\n",
  );
  await writeFile(
    path.join(output, "index.html"),
    `<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Symbiose · ${phase}</title><style>body{background:#10251c;color:#f5f8ef;font:14px system-ui;margin:30px}main{display:grid;grid-template-columns:1fr 1fr;gap:25px}figure{margin:0}img{width:100%}a{color:inherit}@media(max-width:800px){main{grid-template-columns:1fr}}</style><h1>Symbiose · ${phase} · ${fallback ? "2D" : "WebGL"}</h1><a href="report.json">Mesures brutes</a><main>${scenes.map((s) => `<figure><h2>${s.id}</h2><a href="${s.screenshot}"><img src="${s.screenshot}" alt="Chapitre ${s.id}"></a></figure>`).join("")}</main></html>`,
  );
  console.log(
    JSON.stringify(
      {
        output,
        startupMs,
        idleRenderDelta: report.idleRenderDelta,
        measurements: measurements.map((m) => ({
          transition: m.transition,
          fps: m.rendered.fps,
          p95: m.rendered.p95Ms,
          drawCalls: m.finalState.drawCalls,
          renderer: m.finalState.renderer,
        })),
        errors,
        external,
      },
      null,
      2,
    ),
  );
  if (errors.length || external.length) process.exitCode = 1;
} finally {
  await browser.close();
}
