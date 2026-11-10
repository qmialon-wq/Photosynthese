import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import LoginTransition from "../../src/components/symbiose/LoginTransition.vue";
import { useWallpaper } from "../../src/composables/useWallpaper";
import {
  createLoginTransition,
  LOGIN_TRANSITION_MS,
  LOGIN_TRANSITION_REDUCED_MS,
  useLoginTransition,
} from "../../src/composables/useLoginTransition";

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

describe("cycle de vie de la transition de connexion", () => {
  it("reste inactive sans déclenchement et ne dépend pas de la disponibilité des données", () => {
    const store = createLoginTransition();
    vi.runAllTimers();
    expect(store.active.value).toBe(false);
    expect(vi.getTimerCount()).toBe(0);
  });

  it.each(["completed", "skipped", "cancelled"] as const)(
    "termine via %s une seule fois et nettoie le délai",
    async (reason) => {
      const store = createLoginTransition();
      const run = store.start(false);
      expect(store.active.value).toBe(true);
      run.finish(reason);
      run.finish("timeout");
      expect(await run.finished).toBe(reason);
      expect(store.active.value).toBe(false);
      expect(vi.getTimerCount()).toBe(0);
    },
  );

  it("retire la couche même sans composant monté ou événement CSS", async () => {
    const store = createLoginTransition();
    const run = store.start(false);
    await vi.advanceTimersByTimeAsync(LOGIN_TRANSITION_MS + 299);
    expect(store.active.value).toBe(true);
    await vi.advanceTimersByTimeAsync(1);
    expect(await run.finished).toBe("timeout");
    expect(store.active.value).toBe(false);
    expect(vi.getTimerCount()).toBe(0);
  });

  it("ne laisse pas une ancienne navigation terminer une nouvelle animation", async () => {
    const store = createLoginTransition();
    const first = store.start(false);
    const second = store.start(false);
    expect(await first.finished).toBe("replaced");
    first.finish("cancelled");
    expect(store.active.value).toBe(true);
    expect(vi.getTimerCount()).toBe(1);
    second.finish();
    expect(await second.finished).toBe("completed");
    expect(vi.getTimerCount()).toBe(0);
  });

  it("borne aussi la variante statique pour les animations réduites", async () => {
    const store = createLoginTransition();
    const run = store.start(true);
    expect(store.reduced.value).toBe(true);
    await vi.advanceTimersByTimeAsync(LOGIN_TRANSITION_REDUCED_MS + 300);
    expect(await run.finished).toBe("timeout");
    expect(store.active.value).toBe(false);
  });

  it("nettoie une animation en cours au démontage du composant global", async () => {
    const wrapper = mount(LoginTransition);
    const run = useLoginTransition().start(false);
    await nextTick();
    expect(wrapper.findAll(".deer-leg")).toHaveLength(4);
    wrapper.unmount();
    expect(await run.finished).toBe("cancelled");
    expect(useLoginTransition().active.value).toBe(false);
  });

  it("termine immédiatement lorsque la préférence Symbiose est activée pendant le galop", async () => {
    const wrapper = mount(LoginTransition);
    const run = useLoginTransition().start(false);
    await nextTick();
    useWallpaper().setReduceMotion(true);
    await nextTick();
    expect(await run.finished).toBe("skipped");
    expect(wrapper.find(".login-transition").exists()).toBe(false);
    expect(vi.getTimerCount()).toBe(0);
    wrapper.unmount();
    useWallpaper().setReduceMotion(false);
  });
});
