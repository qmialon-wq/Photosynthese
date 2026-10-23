import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import PrimeVue from "primevue/config";
import Button from "primevue/button";
import ParcelProject from "../../src/components/ParcelProject.vue";
import LoadState from "../../src/components/LoadState.vue";

let calls: Array<{ path: string; options: RequestInit }>;
const profile = {
  area_m2: 2500,
  land_type: "pasture",
  project_type: "housing",
  locality: "Caen",
  details: "",
};
beforeEach(() => {
  calls = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (path: string, options: RequestInit = {}) => {
      calls.push({ path, options });
      let result: unknown = {
        profile: { revision: 1, profile },
        dossier: null,
      };
      if (path.endsWith("/options"))
        result = {
          land_types: { pasture: "Pâturage" },
          project_types: { housing: "Habitation" },
        };
      if (options.method === "PUT") result = { revision: 2, profile };
      return new Response(JSON.stringify(result), { status: 200 });
    }),
  );
});
afterEach(() => vi.unstubAllGlobals());
const global = {
  plugins: [PrimeVue],
  components: { PButton: Button, LoadState },
};
describe("parcelle et dossier", () => {
  it("restaure le formulaire du backend et conserve sa révision à l'enregistrement", async () => {
    const wrapper = mount(ParcelProject, {
      props: { videoId: "v", analysisId: "", completed: false },
      global,
    });
    await flushPromises();
    expect(
      (wrapper.find('input[type="number"]').element as HTMLInputElement).value,
    ).toBe("2500");
    const saved = await (
      wrapper.vm as unknown as { save: () => Promise<number> }
    ).save();
    expect(saved).toBe(2);
    const request = calls.find((c) => c.options.method === "PUT")!;
    expect(JSON.parse(request.options.body as string)).toEqual({
      ...profile,
      expected_revision: 1,
    });
    wrapper.unmount();
  });
  it("permet l'analyse seule sans imposer le questionnaire", async () => {
    const wrapper = mount(ParcelProject, {
      props: { videoId: "v", analysisId: "", completed: false },
      global,
    });
    await flushPromises();
    await wrapper.find('input[type="checkbox"]').setValue(false);
    expect(wrapper.find('input[type="number"]').exists()).toBe(false);
    expect(
      await (wrapper.vm as unknown as { save: () => Promise<null> }).save(),
    ).toBeNull();
    expect(calls.some((c) => c.options.method === "PUT")).toBe(false);
    wrapper.unmount();
  });
});
