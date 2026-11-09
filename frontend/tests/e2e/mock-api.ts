import type { Page } from "@playwright/test";

// Existing feature scenarios run as an explicitly authenticated administrator.
// Authentication scenarios use their own responses and exercise unauthenticated routes too.
export async function mockApi(
  page: Page,
  handler: Parameters<Page["route"]>[1],
) {
  await page.addInitScript(() =>
    localStorage.setItem("symbiose:data-mode:v1", "real"),
  );
  return page.route("**/api/**", (route, request) => {
    if (new URL(request.url()).pathname === "/api/auth/me")
      return route.fulfill({
        json: {
          user: {
            id: "test-admin",
            email: "admin@example.test",
            display_name: "Admin test",
            role: "admin",
            created_at: "2026-10-27T10:00:00Z",
            deleted_at: null,
          },
          csrf_token: "test-csrf",
        },
      });
    return handler(route, request);
  });
}
