import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

async function openPitch(page: Page, fallback = true) {
  await page.route("**/api/**", (route) =>
    route.fulfill(
      new URL(route.request().url()).pathname.endsWith("/auth/me")
        ? { status: 401, json: { detail: "Connexion requise" } }
        : { json: { setup_required: false, registration_open: true } },
    ),
  );
  if (fallback)
    await page.addInitScript(() => {
      const original = HTMLCanvasElement.prototype.getContext;
      HTMLCanvasElement.prototype.getContext = function (
        type: any,
        ...args: any[]
      ) {
        if (type === "webgl2") return null;
        return original.call(this, type, ...args);
      } as typeof original;
    });
  await page.goto("/");
  await expect(page.locator(".sx-stage")).toHaveClass(/sx-stage--ready/, {
    timeout: 45000,
  });
}
async function chapter(page: Page, name: string, id: string) {
  await page.getByRole("button", { name }).click();
  await expect(page.locator(".sx-pitch-content")).toHaveAttribute(
    "data-chapter",
    id,
  );
  await expect(page.locator(".sx-pitch-scene")).toHaveAttribute(
    "aria-label",
    /.+/,
  );
}
async function fixtureVideo(page: Page) {
  // An explicit test signal, never shipped or presented as the product demonstration.
  return Buffer.from(
    await page.evaluate(async () => {
      const canvas = document.createElement("canvas");
      canvas.width = 160;
      canvas.height = 90;
      const context = canvas.getContext("2d")!;
      const stream = canvas.captureStream(12);
      const recorder = new MediaRecorder(stream, {
        mimeType: "video/webm;codecs=vp8",
      });
      const chunks: Blob[] = [];
      recorder.ondataavailable = (e) => chunks.push(e.data);
      const done = new Promise<void>((resolve) => {
        recorder.onstop = () => resolve();
      });
      recorder.start();
      for (let i = 0; i < 18; i++) {
        context.fillStyle = i % 2 ? "#325535" : "#264225";
        context.fillRect(0, 0, 160, 90);
        context.fillStyle = "white";
        context.fillText("TEST MEDIA", 20, 40);
        await new Promise((resolve) => setTimeout(resolve, 90));
      }
      recorder.stop();
      await done;
      stream.getTracks().forEach((track) => track.stop());
      return [
        ...new Uint8Array(
          await new Blob(chunks, { type: "video/webm" }).arrayBuffer(),
        ),
      ];
    }),
  );
}

test("eight sourced scenes, archived observations, jury coverage and final application link", async ({
  page,
}) => {
  const external: string[] = [],
    errors: string[] = [];
  page.on("request", (request) => {
    if (
      !/^(localhost|127\.0\.0\.1)$/.test(new URL(request.url()).hostname) &&
      !request.url().startsWith("blob:")
    )
      external.push(request.url());
  });
  page.on("pageerror", (error) => errors.push(error.message));
  await page.setViewportSize({ width: 1440, height: 1000 });
  await openPitch(page);
  await expect(
    page.getByRole("heading", { name: /Voir le vivant/ }),
  ).toBeVisible();
  await page.screenshot({ path: "../output/symbiose/pitch/01-probleme.png" });
  await chapter(page, "3. Rivières", "rivers");
  await page
    .getByText("Résultats vérifiés · deux points normands", { exact: true })
    .click();
  await expect(page.getByText("250008148", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Caen", exact: true }).click();
  await expect(
    page.getByText("Aucun objet renvoyé", { exact: true }),
  ).toHaveCount(4);
  await expect(page.getByText(/ARCHIVES IGN/)).toBeVisible();
  await page.screenshot({ path: "../output/symbiose/pitch/03-donnees.png" });
  await chapter(page, "4. Monde sous-marin", "underwater");
  await expect(
    page.getByText("Perspective · non opérationnelle", { exact: true }),
  ).toBeVisible();
  await chapter(page, "5. Zone humide", "wetland");
  await page.getByRole("button", { name: "03 Reconnaissance" }).click();
  await expect(page.locator(".sx-pipeline-detail")).toContainText(
    "MegaDetector localise",
  );
  await expect(page.locator(".sx-pipeline-detail")).toContainText(
    "le suivi relie",
  );
  await page.screenshot({ path: "../output/symbiose/pitch/05-moteur.png" });
  await page
    .getByRole("button", { name: "Démonstration", exact: true })
    .click();
  await expect(
    page.getByText("Vidéo produit de 90 s non fournie", { exact: true }),
  ).toBeVisible();
  await expect(page.locator("video")).toHaveCount(0);
  await expect(page.locator(".sx-demo img")).toBeVisible();
  await page
    .locator(".sx-demo img")
    .evaluate((img: HTMLImageElement) => img.decode());
  const posterBox = await page.locator(".sx-demo img").boundingBox();
  expect(posterBox!.width / posterBox!.height).toBeCloseTo(1907 / 895, 1);
  const fileChoiceBox = await page
    .locator('.sx-demo input[type="file"]')
    .boundingBox();
  const demoContentBox = await page.locator(".sx-pitch-content").boundingBox();
  expect(fileChoiceBox!.y + fileChoiceBox!.height).toBeLessThanOrEqual(
    demoContentBox!.y + demoContentBox!.height,
  );
  await page.screenshot({
    path: "../output/symbiose/pitch/06-demonstration.png",
  });
  await chapter(page, "8. Forêt nocturne", "night-forest");
  await expect(
    page.getByRole("heading", { name: /Pour mieux protéger le vivant/ }),
  ).toBeVisible();
  await expect(page.getByText(/ARQ · Arden, Romain et Quentin/)).toBeVisible();
  const cta = page.getByRole("link", {
    name: "Commencer l’expérience Symbiose",
  });
  await expect(cta).toHaveAttribute("href", "/connexion");
  await page.screenshot({ path: "../output/symbiose/pitch/08-conclusion.png" });
  await page.getByRole("button", { name: "Sources et texte oral" }).click();
  await expect(
    page.getByRole("heading", { name: /Les preuves, les mots/ }),
  ).toBeVisible();
  await expect(page.getByText(/Attendus vérifiés/)).toBeVisible();
  await page
    .getByRole("button", { name: "Attendus du jury", exact: true })
    .click();
  await expect(page.getByRole("table")).toBeVisible();
  await expect(page.getByRole("row")).toHaveCount(13);
  await page.getByRole("button", { name: "Pitch chronométré" }).click();
  await expect(page.locator(".sx-speaker-chapter")).toHaveCount(8);
  await page.getByRole("button", { name: "Fermer le projet" }).click();
  await cta.click();
  await expect(page).toHaveURL(/\/connexion$/);
  expect(external).toEqual([]);
  expect(errors).toEqual([]);
});

test("presentation keyboard, narrative stops, reverse navigation and reduced motion", async ({
  page,
}) => {
  await openPitch(page);
  await page.getByRole("button", { name: "Mode exploration" }).click();
  await page.locator("#main-content").focus();
  await page.keyboard.press("ArrowRight");
  await expect(page.locator(".sx-pitch-content")).toHaveAttribute(
    "data-chapter",
    "sky",
  );
  await expect(page.locator(".sx-counter")).toHaveText("0:35 / 5:00");
  await page.keyboard.press("ArrowLeft");
  await expect(page.locator(".sx-pitch-content")).toHaveAttribute(
    "data-chapter",
    "forest",
  );
  await page.keyboard.press("Space");
  await expect(
    page.getByRole("button", { name: "Mettre en pause", exact: true }),
  ).toBeVisible();
  await page.keyboard.press("Space");
  await expect(
    page.getByRole("button", { name: "Lire le récit", exact: true }),
  ).toBeVisible();
  // Start just before the first chapter boundary to check its actual automatic stop.
  await page.getByRole("slider").fill("8.2");
  await expect
    .poll(async () =>
      Number(
        await page.locator(".sx-experience").getAttribute("data-progress"),
      ),
    )
    .toBeCloseTo(0.082, 4);
  await page
    .getByRole("button", { name: "Lire le récit", exact: true })
    .click();
  await expect(page.locator(".sx-pitch-content")).toHaveAttribute(
    "data-chapter",
    "sky",
  );
  await expect(
    page.getByRole("button", { name: "Lire le récit", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Démonstration", exact: true })
    .click();
  await expect(page.locator(".sx-counter")).toHaveText("2:30 / 5:00");
  await expect(
    page.getByRole("button", { name: "Lire le récit" }),
  ).toBeDisabled();
  await page.emulateMedia({ reducedMotion: "reduce" });
  await expect(page.getByRole("button", { name: "Lire le récit" })).toHaveCount(
    0,
  );
  await page.locator("#main-content").focus();
  await page.keyboard.press("End");
  await expect(page.locator(".sx-counter")).toHaveText("5:00 / 5:00");
  await page.keyboard.press("Home");
  await expect(page.locator(".sx-counter")).toHaveText("0:00 / 5:00");
});

test("a real local media file stays manual, pauses for sources and releases on chapter departure", async ({
  page,
}) => {
  await openPitch(page);
  const bytes = await fixtureVideo(page);
  await page
    .getByRole("button", { name: "Démonstration", exact: true })
    .click();
  await expect(page.locator(".sx-pitch-content")).toHaveAttribute(
    "data-chapter",
    "meadow",
  );
  await page.locator('.sx-demo input[type="file"]').setInputFiles({
    name: "test-signal.webm",
    mimeType: "video/webm",
    buffer: bytes,
  });
  const video = page.locator("video");
  await expect(video).toHaveAttribute("controls", "");
  await expect(video).not.toHaveAttribute("autoplay");
  expect(await video.evaluate((v: HTMLVideoElement) => v.paused)).toBe(true);
  await page
    .getByRole("button", { name: "Lancer la vidéo", exact: true })
    .click();
  await expect
    .poll(() => video.evaluate((v: HTMLVideoElement) => v.currentTime))
    .toBeGreaterThan(0.1);
  await page.getByRole("button", { name: "Mettre la vidéo en pause" }).click();
  expect(await video.evaluate((v: HTMLVideoElement) => v.paused)).toBe(true);
  await page
    .getByRole("button", { name: "Lancer la vidéo", exact: true })
    .click();
  await page.getByRole("button", { name: "Le projet", exact: true }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  expect(await video.evaluate((v: HTMLVideoElement) => v.paused)).toBe(true);
  await page.keyboard.press("Escape");
  expect(await video.evaluate((v: HTMLVideoElement) => v.paused)).toBe(true);
  const beforeWheel = Number(
    await page.locator(".sx-experience").getAttribute("data-progress"),
  );
  const videoBox = (await video.boundingBox())!;
  await page.mouse.move(
    videoBox.x + videoBox.width / 2,
    videoBox.y + videoBox.height / 2,
  );
  const panel = page.locator(".sx-pitch-content");
  expect(
    await panel.evaluate((el) => el.scrollHeight - el.clientHeight),
  ).toBeGreaterThan(0);
  await page.mouse.wheel(0, 100);
  await expect
    .poll(() => panel.evaluate((el) => el.scrollTop))
    .toBeGreaterThan(0);
  await expect(video).toBeVisible();
  expect(
    Number(await page.locator(".sx-experience").getAttribute("data-progress")),
  ).toBeCloseTo(beforeWheel, 6);
  // Once the pointer leaves the independently scrollable article, native page
  // scrolling must take control again without falling below the demo boundary.
  await page.mouse.move((await page.viewportSize())!.width - 8, 300);
  await page.mouse.wheel(0, 1000);
  await expect
    .poll(async () =>
      Number(
        await page.locator(".sx-experience").getAttribute("data-progress"),
      ),
    )
    .toBeGreaterThan(beforeWheel + 0.01);
  await page.getByRole("button", { name: "Chapitre suivant" }).click();
  await expect(video).toHaveCount(0);
});

test("mobile scenes and source book remain readable and accessible", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 390, height: 844 });
  await openPitch(page);
  for (const [name, id] of [
    ["1. Forêt", "forest"],
    ["5. Zone humide", "wetland"],
    ["6. Prairie et bocage", "meadow"],
    ["8. Forêt nocturne", "night-forest"],
  ]) {
    await chapter(page, name, id);
    await expect
      .poll(() =>
        page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
      )
      .toBe(true);
    expect(
      (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze())
        .violations,
    ).toEqual([]);
  }
  const finalAction = await page
    .getByRole("link", { name: "Commencer l’expérience Symbiose" })
    .boundingBox();
  const content = await page.locator(".sx-pitch-content").boundingBox();
  expect(finalAction!.y).toBeGreaterThanOrEqual(content!.y);
  expect(finalAction!.y + finalAction!.height).toBeLessThanOrEqual(
    content!.y + content!.height,
  );
  await page.screenshot({
    path: "../output/symbiose/pitch/mobile-conclusion.png",
  });
  await page.getByRole("button", { name: "Le projet", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: /Les preuves, les mots/ }),
  ).toBeVisible();
  expect(
    (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze())
      .violations,
  ).toEqual([]);
});

test("unreadable local media and unavailable fullscreen have explicit fallbacks", async ({
  page,
}) => {
  await openPitch(page);
  await page.evaluate(() => {
    Object.defineProperty(document.documentElement, "requestFullscreen", {
      value: undefined,
      configurable: true,
    });
  });
  await page.getByRole("button", { name: "Plein écran", exact: true }).click();
  await expect(
    page.getByText("Le plein écran n’est pas disponible dans ce navigateur.", {
      exact: true,
    }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Démonstration", exact: true })
    .click();
  await page.locator('.sx-demo input[type="file"]').setInputFiles({
    name: "invalid.webm",
    mimeType: "video/webm",
    buffer: Buffer.from("invalid video fixture"),
  });
  // Some Chromium versions reject the file as soon as its blob URL is assigned.
  // Otherwise explicitly request media loading and assert the same honest fallback.
  await page
    .locator(".sx-demo video")
    .evaluateAll((elements) =>
      elements.forEach((element) => (element as HTMLVideoElement).load()),
    );
  await expect(page.locator(".sx-demo video")).toHaveCount(0);
  await expect(page.getByText(/Vidéo absente ou illisible/)).toBeVisible();
  await expect(page.locator(".sx-demo img")).toBeVisible();
});
