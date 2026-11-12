import { expect, test, type Page } from "@playwright/test";

async function eligibleIcon(page: Page) {
  return page.locator('head link[rel="icon"]').evaluateAll((links) => {
    const eligible = (links as HTMLLinkElement[]).filter(
      (link) => !link.media || matchMedia(link.media).matches,
    );
    return eligible.at(-1)?.getAttribute("href");
  });
}

test.beforeEach(async ({ page }) => {
  await page.route("**/api/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    return route.fulfill({
      json:
        path === "/api/auth/me"
          ? {
              user: {
                id: "favicon-user",
                display_name: "Camille",
                email: null,
                role: "admin",
                created_at: "2026-11-12",
                deleted_at: null,
              },
              csrf_token: "test-csrf",
            }
          : path === "/api/auth/status"
            ? { setup_required: false }
            : [],
    });
  });
});

test("le favicon suit le navigateur après changement de thème et rechargement", async ({
  page,
}) => {
  await page.goto("/connexion");
  for (const colorScheme of ["light", "dark", "light"] as const) {
    await page.emulateMedia({ colorScheme });
    await expect
      .poll(() => eligibleIcon(page))
      .toBe(`/favicon-${colorScheme}.ico`);
    await page.reload();
    await expect
      .poll(() => eligibleIcon(page))
      .toBe(`/favicon-${colorScheme}.ico`);
  }
  const fallback = page.locator('head link[rel="icon"]:not([media])');
  await expect(fallback).toHaveCount(1);
  await expect(fallback).toHaveAttribute("href", "/favicon.ico");
  const fallbackSizes = (await fallback.getAttribute("sizes"))!.split(" ");
  for (const link of await page.locator('head link[rel="icon"][media]').all()) {
    // Matching frame sizes keep the fallback from outranking an adaptive icon.
    const sizes = (await link.getAttribute("sizes"))!.split(" ");
    expect(sizes).toEqual(expect.arrayContaining(fallbackSizes));
  }
});

test("les icônes sont servies comme images et restent lisibles à petite taille", async ({
  page,
  request,
}) => {
  await page.goto("/connexion");
  const links = await page
    .locator('head link[rel*="icon"]')
    .evaluateAll((items) =>
      items.map((item) => (item as HTMLLinkElement).href),
    );
  expect(links).toHaveLength(4);
  for (const url of links) {
    const response = await request.get(url);
    expect(response.status()).toBe(200);
    expect(response.headers()["content-type"]).toMatch(/^image\//);
    if (url.endsWith(".ico")) {
      const bytes = await response.body();
      const frames = url.endsWith("/favicon.ico") ? 3 : 4;
      expect([...bytes.subarray(0, 6)]).toEqual([0, 0, 1, 0, frames, 0]);
      expect(
        [6, 22, 38].map((offset) => [...bytes.subarray(offset, offset + 2)]),
      ).toEqual([
        [16, 16],
        [32, 32],
        [48, 48],
      ]);
      if (frames === 4) {
        // An ICO encodes the 256 px frame's dimensions as zeroes.
        expect([...bytes.subarray(54, 56)]).toEqual([0, 0]);
      }
    }
  }
  for (const variant of ["light", "dark"] as const) {
    for (const size of [16, 32, 48]) {
      const pixels = await page.evaluate(
        async ({ variant, size }) => {
          const image = new Image();
          image.src = `/favicon-${variant}.ico`;
          await image.decode();
          const canvas = document.createElement("canvas");
          canvas.width = canvas.height = size;
          const context = canvas.getContext("2d")!;
          context.drawImage(image, 0, 0, size, size);
          const data = context.getImageData(0, 0, size, size).data;
          const opaque: number[][] = [];
          const bounds = [size, size, -1, -1];
          for (let i = 0; i < data.length; i += 4) {
            if (data[i + 3] > 128) {
              opaque.push([...data.slice(i, i + 3)]);
              const x = (i / 4) % size;
              const y = Math.floor(i / 4 / size);
              bounds[0] = Math.min(bounds[0], x);
              bounds[1] = Math.min(bounds[1], y);
              bounds[2] = Math.max(bounds[2], x);
              bounds[3] = Math.max(bounds[3], y);
            }
          }
          return {
            opaque,
            bounds,
            cornerAlpha: data[3],
            width: image.naturalWidth,
          };
        },
        { variant, size },
      );
      expect(pixels.width).toBe(256);
      expect(pixels.cornerAlpha).toBe(0);
      expect(pixels.opaque.length).toBeGreaterThan(size * size * 0.25);
      const color = variant === "light" ? 0 : 255;
      expect(
        pixels.opaque.every((rgb) =>
          rgb.every((v) => Math.abs(v - color) <= 1),
        ),
      ).toBe(true);
      const [left, top, right, bottom] = pixels.bounds;
      expect(left).toBeGreaterThanOrEqual(1);
      expect(top).toBeGreaterThanOrEqual(1);
      expect(Math.abs(left - (size - 1 - right))).toBeLessThanOrEqual(1);
      expect(Math.abs(top - (size - 1 - bottom))).toBeLessThanOrEqual(1);
    }
  }
});

test("le favicon est commun aux rubriques et indépendant du paysage choisi", async ({
  page,
}) => {
  await page.emulateMedia({ colorScheme: "dark" });
  for (const wallpaper of ["forest", "coast", "night-forest"]) {
    await page.addInitScript((value) => {
      localStorage.setItem("symbiose:wallpaper:v1", value);
    }, wallpaper);
    for (const path of [
      "/connexion",
      "/",
      "/videos",
      "/parcelles",
      "/analyses",
      "/review",
      "/documents",
      "/profil",
      "/admin",
    ]) {
      await page.goto(path);
      await expect.poll(() => eligibleIcon(page)).toBe("/favicon-dark.ico");
      await expect(page.locator('head link[rel="icon"]')).toHaveCount(3);
    }
  }
});
