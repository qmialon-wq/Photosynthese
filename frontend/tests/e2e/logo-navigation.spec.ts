import { test, expect } from "@playwright/test";

for (const role of [null, "client", "admin"] as const) {
  test(`le logo ouvre / depuis chaque espace, session ${role || "absente"}`, async ({
    page,
  }) => {
    await page.route("**/api/**", (route) => {
      const path = new URL(route.request().url()).pathname;
      if (path === "/api/auth/me")
        return route.fulfill(
          role
            ? {
                json: {
                  user: {
                    id: "logo-user",
                    display_name: "Camille",
                    email: null,
                    role,
                    created_at: "2026-11-12",
                    deleted_at: null,
                  },
                  csrf_token: "test-csrf",
                },
              }
            : { status: 401, json: { detail: "Connexion requise" } },
        );
      return route.fulfill({
        json: path === "/api/auth/status" ? { setup_required: false } : [],
      });
    });
    const pages = [
      "/",
      "/connexion",
      "/inscription",
      "/initialisation",
      "/reinitialiser",
    ];
    if (role) pages.push("/videos", "/profil");
    if (role === "admin") pages.push("/admin/models");
    for (const path of pages) {
      await page.goto(path);
      const logo = page.getByRole("link", { name: /Symbiose.*accueil/i });
      await expect(logo).toHaveCount(1);
      await expect(logo).toHaveAttribute("href", "/");
      await logo.click();
      await expect(page).toHaveURL(/\/$/);
      await expect(page.getByRole("heading", { level: 1 })).toContainText(
        role
          ? "Vos observations, simplement."
          : "Le vivant",
      );
      await expect(page.locator(".landing")).toHaveCount(role ? 0 : 1);
    }
  });
}
