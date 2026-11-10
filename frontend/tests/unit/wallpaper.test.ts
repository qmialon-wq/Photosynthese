import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  backgroundIds,
  backgroundThemes,
} from "../../src/config/background-themes";
import {
  createWallpaperStore,
  WALLPAPER_KEY,
  REDUCE_MOTION_KEY,
} from "../../src/composables/useWallpaper";

beforeEach(() => localStorage.clear());
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});
const create = (load = vi.fn(async (_url: string) => {})) =>
  createWallpaperStore({ load, systemReduced: true });

describe("préférences de fond partagées", () => {
  it("restaure uniquement un identifiant valide et charge seulement le fond choisi", async () => {
    localStorage.setItem(WALLPAPER_KEY, "coast");
    const load = vi.fn(async () => {});
    const store = create(load);
    await store.initialize();
    await store.initialize();
    expect(store.selected.value.id).toBe("coast");
    expect(load).toHaveBeenCalledExactlyOnceWith(backgroundThemes[6].image);
  });
  it.each([null, "", "unknown", '{"id":"sky"}', "../sky.webp"])(
    "revient à Forêt pour %s",
    (saved) => {
      if (saved !== null) localStorage.setItem(WALLPAPER_KEY, saved);
      expect(create().selected.value.id).toBe("forest");
    },
  );
  it("sélectionne les huit fonds, persiste et réinitialise seulement le papier peint", async () => {
    localStorage.setItem("symbiose:data-mode:v1", "real");
    const store = create();
    store.setReduceMotion(true);
    for (const id of backgroundIds) {
      expect(await store.setTheme(id)).toBe(true);
      expect(store.selected.value.id).toBe(id);
      expect(localStorage.getItem(WALLPAPER_KEY)).toBe(id);
    }
    await store.reset();
    expect(create().selected.value.id).toBe("forest");
    expect(localStorage.getItem("symbiose:data-mode:v1")).toBe("real");
    expect(localStorage.getItem(REDUCE_MOTION_KEY)).toBe("true");
  });
  it("fonctionne en session même si les accès au stockage lèvent une erreur", async () => {
    const store = createWallpaperStore({
      storage: () => {
        throw new Error("blocked");
      },
      load: async () => {},
      systemReduced: true,
    });
    await store.setTheme("sky");
    store.setReduceMotion(true);
    expect(store.selected.value.id).toBe("sky");
    expect(store.reduceMotion.value).toBe(true);
  });
  it("conserve la photo et la préférence si le chargement échoue, puis permet un nouvel essai", async () => {
    const load = vi
      .fn()
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValue(undefined);
    const store = create(load);
    expect(await store.setTheme("river")).toBe(false);
    expect(store.selected.value.id).toBe("forest");
    expect(localStorage.getItem(WALLPAPER_KEY)).toBeNull();
    expect(store.error.value).toContain("précédent");
    expect(await store.setTheme("river")).toBe(true);
    expect(store.error.value).toBe("");
  });
  it("privilégie le dernier choix si des téléchargements terminent dans le désordre", async () => {
    let release!: () => void;
    const store = createWallpaperStore({
      systemReduced: true,
      load: (url) =>
        url === backgroundThemes[1].image
          ? new Promise<void>((resolve) => {
              release = resolve;
            })
          : Promise.resolve(),
    });
    const slow = store.setTheme("sky");
    await store.setTheme("coast");
    release();
    await slow;
    expect(store.selected.value.id).toBe("coast");
    expect(localStorage.getItem(WALLPAPER_KEY)).toBe("coast");
  });
  it("ignore une restauration en erreur lorsqu’un nouveau choix a réussi", async () => {
    localStorage.setItem(WALLPAPER_KEY, "sky");
    let fail!: (error: Error) => void;
    const store = createWallpaperStore({
      systemReduced: true,
      load: (url) =>
        url === backgroundThemes[1].image
          ? new Promise<void>((_, reject) => {
              fail = reject;
            })
          : Promise.resolve(),
    });
    const initial = store.initialize();
    await store.setTheme("coast");
    fail(new Error("offline"));
    await initial;
    expect(store.selected.value.id).toBe("coast");
    expect(store.error.value).toBe("");
  });
  it("garde deux couches au maximum, termine le fondu et applique immédiatement la réduction système", async () => {
    vi.useFakeTimers();
    vi.stubGlobal("requestAnimationFrame", (fn: FrameRequestCallback) =>
      setTimeout(() => fn(0), 16),
    );
    vi.stubGlobal("cancelAnimationFrame", clearTimeout);
    const store = createWallpaperStore({ load: async () => {} });
    const first = store.setTheme("sky");
    await vi.advanceTimersByTimeAsync(32);
    expect(store.base.value.id).toBe("forest");
    expect(store.incoming.value?.id).toBe("sky");
    expect(store.incomingVisible.value).toBe(true);
    const second = store.setTheme("river");
    const last = store.setTheme("coast");
    await vi.advanceTimersByTimeAsync(650);
    await first;
    expect(store.base.value.id).toBe("sky");
    expect(store.incoming.value?.id).toBe("coast");
    store.setSystemReduced(true);
    await Promise.all([second, last]);
    expect(store.base.value.id).toBe("coast");
    expect(store.incoming.value).toBeNull();
    await store.setTheme("wetland");
    expect(store.base.value.id).toBe("wetland");
    expect(store.incoming.value).toBeNull();
  });
});
