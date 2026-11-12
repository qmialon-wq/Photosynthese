import { test, expect } from "@playwright/test";
import { mockApi } from "./mock-api";

test("les dossiers reprennent la miniature de leur première vidéo et illustrent les dossiers vides", async ({
  page,
}) => {
  const videos = ["second", "first"].map((id) => ({
    id,
    filename: `${id}.mp4`,
    species_candidate: null,
    status: "ready",
    metadata: { poster_url: `/poster-${id}.svg` },
    created_at: "2026-11-12",
  }));
  await page.route("**/poster-*.svg", (route) =>
    route.fulfill({
      contentType: "image/svg+xml",
      body: '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="250"><rect width="400" height="250" fill="#55703f"/></svg>',
    }),
  );
  await mockApi(page, (route) => {
    const path = new URL(route.request().url()).pathname.replace(/^\/api/, "");
    if (path === "/console/videos") return route.fulfill({ json: videos });
    if (path === "/parcels/corpora")
      return route.fulfill({ json: [{ id: "ordered" }, { id: "empty" }] });
    if (path.startsWith("/parcels/corpora/"))
      return route.fulfill({
        json: {
          videos: path.endsWith("/ordered")
            ? [
                { video_id: "first", filename: "first.mp4" },
                { video_id: "second", filename: "second.mp4" },
              ]
            : [],
          profile: {
            profile: {
              locality: path.endsWith("/ordered")
                ? "Dossier avec vidéos"
                : "Dossier sans vidéo",
            },
          },
          dossier: null,
        },
      });
    return route.fulfill({ json: [] });
  });
  await page.goto("/videos");
  const original = page
    .getByRole("img", { name: "Miniature de first.mp4", exact: true })
    .locator("img");
  await expect(original).toHaveAttribute("src", "/poster-first.svg");
  await page.locator('.sym-wheel-link[data-section="/parcelles"]').click();
  const withVideo = page.getByRole("button", {
    name: "Ouvrir le dossier Dossier avec vidéos",
    exact: true,
  });
  await expect(withVideo.locator(".sf-project-thumbnail img")).toHaveAttribute(
    "src",
    "/poster-first.svg",
  );
  const empty = page.getByRole("button", {
    name: "Ouvrir le dossier Dossier sans vidéo",
    exact: true,
  });
  const fallback = empty.getByRole("img", {
    name: "Illustration par défaut : sanglier",
  });
  await expect(fallback).toBeVisible();
  expect(
    await fallback.evaluate(
      (img: HTMLImageElement) => img.complete && img.naturalWidth > 0,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/project-thumbnails.png",
    fullPage: true,
  });
  await page.reload();
  await expect(withVideo.locator(".sf-project-thumbnail img")).toHaveAttribute(
    "src",
    "/poster-first.svg",
  );
});
