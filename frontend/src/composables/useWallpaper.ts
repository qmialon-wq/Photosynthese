import { computed, readonly, ref, shallowRef } from "vue";
import {
  defaultBackground,
  findBackground,
  type BackgroundTheme,
} from "../config/background-themes";

export const WALLPAPER_KEY = "symbiose:wallpaper:v1";
export const REDUCE_MOTION_KEY = "symbiose:reduce-motion:v1";
export const WALLPAPER_FADE_MS = 650;
type StorageAccess = () => Pick<Storage, "getItem" | "setItem">;

function decodeImage(url: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.fetchPriority = "high";
    image.onload = () => image.decode().then(resolve, reject);
    image.onerror = () => reject(new Error("Image unavailable"));
    image.src = url;
  });
}

export function createWallpaperStore(
  options: {
    storage?: StorageAccess;
    load?: (url: string) => Promise<void>;
    systemReduced?: boolean;
  } = {},
) {
  const storage = options.storage ?? (() => localStorage);
  function read(key: string) {
    try {
      return storage().getItem(key);
    } catch {
      return null;
    }
  }
  function save(key: string, value: string) {
    try {
      storage().setItem(key, value);
    } catch {
      /* Session preference remains usable. */
    }
  }
  const base = shallowRef(
    findBackground(read(WALLPAPER_KEY)) ?? defaultBackground,
  );
  const incoming = shallowRef<BackgroundTheme | null>(null);
  const incomingVisible = ref(false);
  const pending = ref<string | null>(null);
  const error = ref("");
  const reduceMotion = ref(read(REDUCE_MOTION_KEY) === "true");
  const systemReduced = ref(options.systemReduced ?? false);
  const reduced = computed(() => reduceMotion.value || systemReduced.value);
  const selected = computed(() => incoming.value ?? base.value);
  const loaded = new Map<string, Promise<void>>();
  function preload(theme: BackgroundTheme) {
    let promise = loaded.get(theme.image);
    if (!promise) {
      promise = (options.load ?? decodeImage)(theme.image).catch((reason) => {
        loaded.delete(theme.image); // A failed image may be retried.
        throw reason;
      });
      loaded.set(theme.image, promise);
    }
    return promise;
  }
  let request = 0;
  let initialized = false;
  let animation: Promise<void> = Promise.resolve();
  let finishAnimation: (() => void) | undefined;
  function setReduceMotion(value: boolean) {
    reduceMotion.value = value;
    save(REDUCE_MOTION_KEY, String(value));
    if (reduced.value) finishAnimation?.();
  }
  function setSystemReduced(value: boolean) {
    systemReduced.value = value;
    if (reduced.value) finishAnimation?.();
  }
  async function initialize() {
    if (initialized) return;
    initialized = true;
    const token = request;
    try {
      await preload(base.value);
    } catch {
      if (token !== request) return;
      base.value = defaultBackground;
      error.value =
        "Le fond enregistré n’a pas pu être chargé. Le fond par défaut est utilisé.";
    }
  }
  async function setTheme(id: string) {
    const target = findBackground(id);
    if (!target) return false;
    const token = ++request;
    pending.value = id;
    error.value = "";
    try {
      await preload(target);
      if (token !== request) return false;
      // Keep at most two photographic layers, even during rapid selections.
      await animation;
      if (token !== request) return false;
      pending.value = null;
      save(WALLPAPER_KEY, target.id);
      if (base.value.id === id) return true;
      if (reduced.value) {
        base.value = target;
        return true;
      }
      incoming.value = target;
      incomingVisible.value = false;
      animation = new Promise<void>((resolve) => {
        let timer: ReturnType<typeof setTimeout>;
        let frame = 0;
        const finish = () => {
          cancelAnimationFrame(frame);
          clearTimeout(timer);
          base.value = target;
          incoming.value = null;
          incomingVisible.value = false;
          finishAnimation = undefined;
          resolve();
        };
        finishAnimation = finish;
        // Two paint frames ensure the decoded incoming layer starts transparent.
        frame = requestAnimationFrame(() => {
          frame = requestAnimationFrame(() => {
            incomingVisible.value = true;
            timer = setTimeout(finish, WALLPAPER_FADE_MS);
          });
        });
      });
      await animation;
      return true;
    } catch {
      if (token === request) {
        pending.value = null;
        error.value =
          "Ce fond n’a pas pu être chargé. Le fond précédent est conservé.";
      }
      return false;
    }
  }
  return {
    base: readonly(base),
    incoming: readonly(incoming),
    incomingVisible: readonly(incomingVisible),
    selected,
    pending: readonly(pending),
    error: readonly(error),
    reduceMotion: readonly(reduceMotion),
    reduced,
    initialize,
    setTheme,
    setReduceMotion,
    setSystemReduced,
    reset: () => setTheme(defaultBackground.id),
  };
}

let shared: ReturnType<typeof createWallpaperStore> | undefined;
export function useWallpaper() {
  if (!shared) {
    const query =
      typeof matchMedia === "function"
        ? matchMedia("(prefers-reduced-motion: reduce)")
        : null;
    shared = createWallpaperStore({ systemReduced: query?.matches });
    query?.addEventListener("change", (event) =>
      shared?.setSystemReduced(event.matches),
    );
  }
  return shared;
}
