import { afterEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import WorkerTerminal from "../../src/components/WorkerTerminal.vue";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});
describe("terminal des workers", () => {
  it("actualise les deux workers et conserve une progression inconnue sans faux pourcentage", async () => {
    vi.useFakeTimers();
    const response = {
      updated_at: "2026-10-27T14:00:00Z",
      workers: [
        {
          role: "vision",
          online: true,
          running: 1,
          queued: 2,
          tasks: [
            {
              id: "vision-task",
              kind: "training",
              status: "running",
              detail: "resnet50",
              progress: { current: 3, total: 10, stage: "Époque 3" },
              logs: [
                {
                  id: 1,
                  message: "Entraînement en cours",
                  created_at: "2026-10-27T14:00:00Z",
                },
              ],
            },
          ],
        },
        {
          role: "documents",
          online: false,
          running: 1,
          queued: 4,
          tasks: [
            {
              id: "document-task",
              kind: "search",
              status: "running",
              detail: "renards",
              progress: {},
              logs: [
                {
                  id: 2,
                  message: "Collecte OpenAlex",
                  created_at: "2026-10-27T14:00:01Z",
                },
              ],
            },
          ],
        },
      ],
    };
    const fetch = vi
      .fn()
      .mockImplementation(async () => ({
        ok: true,
        status: 200,
        json: async () => response,
      }));
    vi.stubGlobal("fetch", fetch);
    const wrapper = mount(WorkerTerminal, {
      global: { stubs: { RouterLink: true } },
    });
    await flushPromises();
    expect(wrapper.text()).toContain("30 %");
    expect(wrapper.text()).toContain("Progression non chiffrée");
    expect(wrapper.text()).toContain("Sans signal récent");
    expect(wrapper.text()).toContain("Collecte OpenAlex");
    await vi.advanceTimersByTimeAsync(2000);
    expect(fetch).toHaveBeenCalledTimes(2);
    wrapper.unmount();
    await vi.advanceTimersByTimeAsync(4000);
    expect(fetch).toHaveBeenCalledTimes(2);
  });
});
