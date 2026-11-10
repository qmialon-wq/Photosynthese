import { onScopeDispose, watchEffect } from "vue";
import { useWallpaper } from "./useWallpaper";

/** Document scope also covers native top layers and teleported PrimeVue dialogs. */
export function useEnvironmentTheme() {
  const wallpaper = useWallpaper();
  const root = document.documentElement;
  const stop = watchEffect(() => {
    root.dataset.environment = wallpaper.selected.value.id;
    root.dataset.reducedMotion = String(wallpaper.reduced.value);
  }, { flush: "sync" });
  onScopeDispose(stop);
  return wallpaper;
}
