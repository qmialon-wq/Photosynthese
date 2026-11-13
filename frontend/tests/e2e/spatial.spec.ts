import { expect, test, type Page } from "@playwright/test";

async function seek(page: Page, index: number, chapter: string) {
  await page.locator(".sx-chapter-nav button").nth(index).click();
  await expect(page.locator(".sx-pitch-content")).toHaveAttribute(
    "data-chapter",
    chapter,
  );
  const expected = [0, 35, 60, 95, 115, 150, 180, 210][index] / 210;
  await page
    .locator(".sx-progress input")
    .evaluate((input: HTMLInputElement, progress) => {
      input.step = "any";
      input.value = String(progress * 100);
      input.dispatchEvent(new Event("input", { bubbles: true }));
    }, expected);
  await page.waitForFunction((expected) => {
    const state =
      document.querySelector<HTMLElement>(".sx-canvas")?.dataset.state;
    return (
      state &&
      Math.abs(JSON.parse(state).progress - expected) < 0.000001 &&
      !JSON.parse(state).assetsPending
    );
  }, expected);
}
const state = (page: Page) =>
  page
    .locator(".sx-canvas")
    .evaluate((el) => JSON.parse((el as HTMLElement).dataset.state!));

test("supplied animals track their projected volumes, reverse deterministically and release skeletal GPU textures", async ({
  page,
}) => {
  test.setTimeout(120000);
  await page.goto("/jury/");
  await expect(page.locator(".sx-stage")).toHaveClass(/sx-stage--ready/, {
    timeout: 45000,
  });
  const first = await state(page);
  expect(first.animals.map((a: any) => a.label)).toEqual(
    expect.arrayContaining(["Chevreuil", "Sanglier", "Pigeon"]),
  );
  await seek(page, 1, "sky");
  expect(
    (await state(page)).animals.filter((a: any) => a.label === "Buse"),
  ).toHaveLength(2);
  await seek(page, 3, "underwater");
  const submerged = await state(page);
  expect(submerged.animals).toHaveLength(3);
  expect(
    submerged.animals.every(
      (a: any) => a.label === "Poisson · espèce à confirmer",
    ),
  ).toBe(true);
  await seek(page, 4, "wetland");
  await seek(page, 7, "night-forest");
  await seek(page, 3, "underwater");
  const reverse = await state(page);
  expect(
    reverse.animals.map((a: any) => [a.id, a.x, a.y, a.width, a.height]),
  ).toEqual(
    submerged.animals.map((a: any) => [a.id, a.x, a.y, a.width, a.height]),
  );
  await seek(page, 0, "forest");

  // First use initializes persistent cliff maps and the shared reflection target.
  // Compare the same pose after warming every scene; repeated trips must not grow GPU resources.
  const chapters = [
    "forest",
    "sky",
    "rivers",
    "underwater",
    "wetland",
    "meadow",
    "coast",
    "night-forest",
  ];
  for (let i = 1; i < chapters.length; i++) await seek(page, i, chapters[i]);
  await seek(page, 0, "forest");
  const warm = await state(page);
  for (let cycle = 0; cycle < 2; cycle++) {
    for (let i = 1; i < chapters.length; i++) await seek(page, i, chapters[i]);
    await seek(page, 0, "forest");
    const repeated = await state(page);
    expect(repeated.textureCount).toBeLessThanOrEqual(warm.textureCount);
    expect(repeated.geometryCount).toBeLessThanOrEqual(warm.geometryCount);
  }
  const settled = await state(page);
  const before = settled.renderCount;
  await page.waitForTimeout(500); // Idle observation, never an animation delay.
  expect((await state(page)).renderCount).toBeLessThanOrEqual(before + 1);
});

test("production offline installation includes the GLB models and PBR textures", async ({
  page,
  context,
}) => {
  test.skip(!process.env.E2E_PRODUCTION, "Requires the emitted service worker");
  test.setTimeout(120000);
  const failed: string[] = [];
  page.on("requestfailed", (request) => {
    if (request.url().includes("experience-models")) failed.push(request.url());
  });
  await page.goto("/jury/");
  await expect(page.locator(".sx-stage")).toHaveClass(/sx-stage--ready/, {
    timeout: 45000,
  });
  await page.locator(".jury-installation summary").click();
  await page
    .getByRole("button", { name: "Installer hors ligne", exact: true })
    .click();
  await expect(page.locator(".jury-installation [role=status]")).toContainText(
    "Installation locale prête",
    { timeout: 65000 },
  );
  await page.locator(".jury-installation summary").click();
  await context.setOffline(true);
  await page.reload();
  await expect(page.locator(".sx-stage")).toHaveClass(/sx-stage--ready/, {
    timeout: 45000,
  });
  await seek(page, 1, "sky");
  await expect(
    page.locator(".sx-animal-label").filter({ hasText: "Buse" }),
  ).toHaveCount(2);
  await seek(page, 3, "underwater");
  await expect(
    page.locator(".sx-animal-label").filter({ hasText: "Poisson" }),
  ).toHaveCount(3);
  expect(failed).toEqual([]);
});
