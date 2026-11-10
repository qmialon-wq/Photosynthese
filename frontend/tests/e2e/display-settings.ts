import { expect, type Page } from "@playwright/test";

export async function openDisplaySettings(page: Page) {
  const source = page.getByRole("combobox", {
    name: "Source de données",
    exact: true,
  });
  if (!(await source.isVisible())) {
    await page.getByRole("button", { name: "Paramètres", exact: true }).click();
    await page
      .getByRole("button", { name: "Paramètres d’affichage", exact: true })
      .click();
  }
  return source;
}
export async function closeDisplaySettings(page: Page) {
  const close = page.locator(".sym-action-panel .sym-close");
  if (await close.isVisible()) await close.click();
}
export async function selectSource(page: Page, mode: string) {
  await (await openDisplaySettings(page)).selectOption(mode);
  await closeDisplaySettings(page);
}
export async function expectSource(page: Page, mode: string) {
  await expect(await openDisplaySettings(page)).toHaveValue(mode);
  await closeDisplaySettings(page);
}
