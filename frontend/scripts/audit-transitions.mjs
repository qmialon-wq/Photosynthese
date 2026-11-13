import { chromium } from "@playwright/test";
import { mkdir, writeFile, readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import path from "node:path";
import { fileURLToPath } from "node:url";
const gpu = process.argv.includes("--gpu"),
  fallback = process.argv.includes("--fallback"),
  baseURL = process.env.E2E_BASE_URL || "http://127.0.0.1:4173";
const directory = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  process.env.AUDIT_OUTPUT || "../../output/symbiose/final/transitions",
  fallback ? "fallback" : gpu ? "gpu" : "software",
);
await mkdir(directory, { recursive: true });
const browser = await chromium.launch(
  gpu && process.platform === "win32"
    ? { args: ["--use-angle=d3d11", "--ignore-gpu-blocklist"] }
    : {},
);
const errors = [],
  records = [],
  performanceReports = [];
try {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 900 },
  });
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (
      message.type() === "error" &&
      !message.text().includes("401") &&
      !fallback
    )
      errors.push(message.text());
  });
  await page.route("**/api/**", (route) =>
    route.fulfill({ status: 401, json: { detail: "Public audit" } }),
  );
  if (fallback)
    await page.addInitScript(() => {
      const original = HTMLCanvasElement.prototype.getContext;
      HTMLCanvasElement.prototype.getContext = function (type, ...args) {
        if (type === "webgl2") return null;
        return original.call(this, type, ...args);
      };
    });
  await page.goto(`${baseURL}/?debug=transitions`);
  await page
    .locator(fallback ? ".sx-fallback-scene" : ".sx-stage--ready")
    .waitFor({ timeout: 45000 });
  if (!fallback)
    await page.waitForFunction(
      () => !!document.querySelector(".sx-canvas")?.dataset.state,
    );
  await page.locator(".sx-canvas").evaluateAll((elements) =>
    elements.forEach((element) => {
      element.style.transition = "none";
      element.style.opacity = "1";
    }),
  );
  const specs = await page
    .getByLabel("Transition à inspecter")
    .locator("option")
    .evaluateAll((options) =>
      options.map((option) => ({
        id: option.value,
        name: option.textContent,
        start: Number(option.dataset.start),
        end: Number(option.dataset.end),
      })),
    );
  async function seek(spec, p) {
    await page.getByLabel("Progression de la transition").fill(String(p));
    const expected = (spec.start + (spec.end - spec.start) * p) / 210;
    await page.waitForFunction(
      ({ expected, fallback }) => {
        const element = document.querySelector(
          fallback ? ".sx-experience" : ".sx-canvas",
        );
        const current = fallback
          ? Number(element?.dataset.progress)
          : element?.dataset.state
            ? JSON.parse(element.dataset.state).progress
            : -1;
        const logical =
          scrollY /
          (document.querySelector(".sx-experience").getBoundingClientRect()
            .height -
            innerHeight);
        return (
          Math.abs(current - expected) < 0.00008 &&
          Math.abs(current - logical) <
            1 /
              Math.max(
                1,
                document.querySelector(".sx-experience").getBoundingClientRect()
                  .height - innerHeight,
              )
        );
      },
      { expected, fallback },
    );
    await page.waitForFunction(() => {
      const state = document.querySelector(".sx-canvas")?.dataset.state;
      return !state || !JSON.parse(state).assetsPending;
    });
    // Let the rounded GSAP scrub settle completely before comparing pixels.
    await page.evaluate(async () => {
      let last = "",
        stable = 0;
      await new Promise((resolve) => {
        function frame() {
          const state =
            document.querySelector(".sx-canvas")?.dataset.state ??
            document.querySelector(".sx-experience")?.dataset.progress;
          stable = state === last ? stable + 1 : 0;
          last = state;
          if (stable >= 4) resolve();
          else requestAnimationFrame(frame);
        }
        requestAnimationFrame(frame);
      });
    });
    if (fallback) {
      await page.waitForFunction(
        () =>
          !Array.from(
            document.querySelectorAll(".sx-fallback-scene [role=status]"),
          ).some((element) => element.offsetParent !== null),
      );
      await page
        .locator(".sx-fallback-scene img")
        .evaluateAll((images) =>
          Promise.all(images.map((image) => image.decode())),
        );
    }
    return fallback
      ? { progress: expected }
      : await page
          .locator(".sx-canvas")
          .evaluate((element) => JSON.parse(element.dataset.state));
  }
  async function capture(file) {
    await page
      .locator(".sx-debug-panel")
      .evaluate((element) => (element.style.visibility = "hidden"));
    const bytes = await page.screenshot({ path: file });
    await page
      .locator(".sx-debug-panel")
      .evaluate((element) => (element.style.visibility = "visible"));
    return createHash("sha256").update(bytes).digest("hex");
  }
  async function comparePixels(before, after) {
    const images = await Promise.all(
      [before, after].map(async (file) =>
        (await readFile(file)).toString("base64"),
      ),
    );
    return page.evaluate(async (images) => {
      const bitmaps = await Promise.all(
        images.map(async (image) =>
          createImageBitmap(
            await (await fetch(`data:image/png;base64,${image}`)).blob(),
          ),
        ),
      );
      const surface = document.createElement("canvas");
      surface.width = bitmaps[0].width;
      surface.height = bitmaps[0].height;
      const ctx = surface.getContext("2d", { willReadFrequently: true });
      ctx.drawImage(bitmaps[0], 0, 0);
      const a = ctx.getImageData(0, 0, surface.width, surface.height).data;
      ctx.clearRect(0, 0, surface.width, surface.height);
      ctx.drawImage(bitmaps[1], 0, 0);
      const b = ctx.getImageData(0, 0, surface.width, surface.height).data;
      let changedPixels = 0,
        maxChannelDelta = 0;
      for (let i = 0; i < a.length; i += 4) {
        let changed = false;
        for (let channel = 0; channel < 3; channel++) {
          const delta = Math.abs(a[i + channel] - b[i + channel]);
          maxChannelDelta = Math.max(maxChannelDelta, delta);
          changed ||= delta > 0;
        }
        if (changed) changedPixels++;
      }
      bitmaps.forEach((bitmap) => bitmap.close());
      const fraction = changedPixels / (surface.width * surface.height);
      return {
        changedPixels,
        maxChannelDelta,
        fraction,
        withinTolerance: maxChannelDelta <= 8 && fraction <= 0.0001,
      };
    }, images);
  }
  for (const spec of specs) {
    await page.getByLabel("Transition à inspecter").selectOption(spec.id);
    const states = [];
    for (const p of [0, 0.25, 0.5, 0.75, 1]) {
      const state = await seek(spec, p);
      const file = path.join(
        directory,
        `${spec.id}-${String(Math.round(p * 100)).padStart(3, "0")}.png`,
      );
      const sha256 = await capture(file);
      states.push({ p, state, screenshot: path.basename(file), sha256 });
    }
    for (const p of [1, 0.75, 0.5, 0.25, 0]) {
      const state = await seek(spec, p);
      if (!fallback) {
        const original = states.find((item) => item.p === p).state;
        if (
          Math.hypot(
            ...state.position.map(
              (value, index) => value - original.position[index],
            ),
          ) > 0.02
        )
          errors.push(`Non-reversible pose: ${spec.id} ${p}`);
      }
    }
    await seek(spec, 0.5);
    const replayHash = await capture(
      path.join(directory, `${spec.id}-replay-050.png`),
    );
    const replayComparison =
      states[2].sha256 === replayHash
        ? {
            changedPixels: 0,
            maxChannelDelta: 0,
            fraction: 0,
            withinTolerance: true,
          }
        : await comparePixels(
            path.join(directory, states[2].screenshot),
            path.join(directory, `${spec.id}-replay-050.png`),
          );
    records.push({
      id: spec.id,
      name: spec.name,
      states,
      replayPixelIdentical: states[2].sha256 === replayHash,
      replayComparison,
    });
    if (!replayComparison.withinTolerance)
      errors.push(`Replay pixels differ: ${spec.id}`);
    if (!fallback) {
      const measurement = await page.evaluate(async ({ start, end }) => {
        const slider = document.querySelector(
            '[aria-label="Progression de la transition"]',
          ),
          canvas = document.querySelector(".sx-canvas"),
          deltas = [];
        let previous = performance.now(),
          initial = 0;
        const begun = performance.now();
        await new Promise((resolve) => {
          function frame(now) {
            const t = Math.min(1, (now - begun) / 3500);
            slider.value = String(t < 0.5 ? t * 2 : 2 - t * 2);
            slider.dispatchEvent(new Event("input", { bubbles: true }));
            if (now - begun > 700) {
              if (!initial) initial = Number(canvas.dataset.renderCount);
              deltas.push(now - previous);
            }
            previous = now;
            if (t < 1) requestAnimationFrame(frame);
            else resolve();
          }
          requestAnimationFrame(frame);
        });
        deltas.sort((a, b) => a - b);
        const duration = deltas.reduce((sum, value) => sum + value, 0),
          state = JSON.parse(canvas.dataset.state);
        return {
          rafFps: Math.round((deltas.length * 1000) / duration),
          renderedFps: Math.round(
            ((state.renderCount - initial) * 1000) / duration,
          ),
          p95FrameMs: Number(
            deltas[Math.floor(deltas.length * 0.95)].toFixed(2),
          ),
          drawCalls: state.drawCalls,
          triangles: state.triangles,
          quality: state.quality,
          pixelRatio: state.pixelRatio,
          renderer: state.renderer,
        };
      }, spec);
      performanceReports.push({ id: spec.id, ...measurement });
    }
  }
  const result = {
    date: new Date().toISOString(),
    browser: browser.version(),
    baseURL,
    mode: fallback
      ? "2d-spatial-masks"
      : gpu
        ? "hardware-requested"
        : "default",
    viewport: { width: 1440, height: 900 },
    records,
    performance: performanceReports,
    errors,
  };
  await page.getByLabel("Transition à inspecter").selectOption("immersion");
  await seek(
    specs.find((spec) => spec.id === "immersion"),
    0.5,
  );
  await page.screenshot({ path: path.join(directory, "debug-panel.png") });
  await writeFile(
    path.join(directory, "report.json"),
    JSON.stringify(result, null, 2) + "\n",
  );
  const html = `<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Symbiose — états intermédiaires</title><style>body{margin:30px;background:#0b211b;color:#f5f8ef;font:14px system-ui}section{margin:35px 0}article{display:grid;grid-template-columns:repeat(5,1fr);gap:8px}img{width:100%;height:auto}figure{margin:0}figcaption{font-size:11px;margin-top:8px}@media(max-width:800px){article{grid-template-columns:1fr 1fr}}</style><h1>Sept raccords · états 0 / 25 / 50 / 75 / 100 %</h1><p>Reconstruction d’intention 3D et calques générés. Les captures ne sont pas des prises de vue géolocalisées.</p>${records.map((record) => `<section><h2>${record.name}</h2><article>${record.states.map((state) => `<figure><a href="${state.screenshot}"><img src="${state.screenshot}" alt="${record.id}, progression ${state.p * 100} %"></a><figcaption>${state.p * 100} %</figcaption></figure>`).join("")}</article><p>Rejeu à 50 % : pixels ${record.replayPixelIdentical ? "identiques" : "différents — inspection requise"}.</p></section>`).join("")}</html>`;
  await writeFile(path.join(directory, "index.html"), html);
  console.log(
    JSON.stringify(
      {
        directory,
        states: records.length * 5,
        replayIdentical: records.filter((r) => r.replayPixelIdentical).length,
        replayWithinTolerance: records.filter(
          (r) => r.replayComparison.withinTolerance,
        ).length,
        performance: performanceReports,
        errors,
      },
      null,
      2,
    ),
  );
  if (errors.length) process.exitCode = 1;
} finally {
  await browser.close();
}
