import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { flushPromises } from "@vue/test-utils";
import { acceptSession, clearSession, auth } from "../../src/auth-state";
import {
  clientGuide,
  openClientGuide,
  guideStep,
  dismissClientGuide,
  resetClientGuide,
  shouldShowClientGuide,
} from "../../src/client-guide";
import { clientGuideCards } from "../../src/data/client-guide";

let account = 0;
beforeEach(() => {
  clearSession();
  resetClientGuide();
  acceptSession({
    user: {
      id: `guide-${++account}`,
      display_name: "Camille",
      role: "client",
      email: null,
      created_at: "2026-11-12",
      deleted_at: null,
      client_guide_seen_at: null,
    },
    csrf_token: "test-csrf",
  });
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});
it("propose le guide une fois et permet de le relancer à la première carte", async () => {
  const fetch = vi.fn(
    async () =>
      new Response(JSON.stringify({ seen_at: "2026-11-12T10:00:00Z" })),
  );
  vi.stubGlobal("fetch", fetch);
  expect(shouldShowClientGuide()).toBe(true);
  openClientGuide();
  guideStep(4);
  await dismissClientGuide();
  expect(shouldShowClientGuide()).toBe(false);
  expect(auth.user?.client_guide_seen_at).toBe("2026-11-12T10:00:00Z");
  expect(fetch).toHaveBeenCalledTimes(1);
  openClientGuide();
  expect(clientGuide.step.value).toBe(0);
  expect(clientGuide.open.value).toBe(true);
});
it("ne réouvre pas automatiquement en boucle si la mémorisation échoue", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async () =>
        new Response(JSON.stringify({ detail: "Indisponible" }), {
          status: 503,
        }),
    ),
  );
  await dismissClientGuide();
  expect(clientGuide.open.value).toBe(false);
  expect(auth.user?.client_guide_seen_at).toBeNull();
  expect(shouldShowClientGuide()).toBe(false);
  expect(clientGuide.error.value).toContain("mémorisée");
});
it("un visiteur peut lire l'aide sans écriture ni session", async () => {
  clearSession();
  const fetch = vi.fn();
  vi.stubGlobal("fetch", fetch);
  expect(shouldShowClientGuide()).toBe(false);
  openClientGuide();
  await dismissClientGuide();
  expect(fetch).not.toHaveBeenCalled();
});
it("ne modifie pas le nouveau compte après une réponse tardive", async () => {
  let respond!: (response: Response) => void;
  vi.stubGlobal(
    "fetch",
    vi.fn(
      () =>
        new Promise<Response>((resolve) => {
          respond = resolve;
        }),
    ),
  );
  const pending = dismissClientGuide();
  await flushPromises();
  acceptSession({
    user: { ...auth.user!, id: "different-account" },
    csrf_token: "new-csrf",
  });
  respond(new Response(JSON.stringify({ seen_at: "2026-11-12" })));
  await pending;
  expect(auth.user?.client_guide_seen_at).toBeNull();
});
it("reste un guide court de huit cartes, sans diaporama automatique", () => {
  expect(clientGuideCards).toHaveLength(8);
  const words = clientGuideCards
    .flatMap((card) => [card.title, card.intro, ...card.bullets])
    .join(" ")
    .split(/\s+/).length;
  expect(words).toBeLessThanOrEqual(650);
});
