import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import PrimeVue from "primevue/config";
import Button from "primevue/button";
import Tag from "primevue/tag";
import BoxEditor from "../../src/components/BoxEditor.vue";
import LoadState from "../../src/components/LoadState.vue";
import StatusBadge from "../../src/components/StatusBadge.vue";
import MetricsPanel from "../../src/components/MetricsPanel.vue";
import { auth, clearSession } from "../../src/auth-state";
import { api } from "../../src/api";

const global = {
  plugins: [PrimeVue],
  components: { PButton: Button, PTag: Tag },
};
beforeEach(() => {
  localStorage.clear();
  clearSession();
});
describe("composants de la console", () => {
  it("signale les erreurs et permet de réessayer", async () => {
    const wrapper = mount(LoadState, {
      props: { error: "Base indisponible" },
      global,
    });
    expect(wrapper.get('[role="alert"]').text()).toContain("Base indisponible");
    await wrapper.get("button").trigger("click");
    expect(wrapper.emitted("retry")).toHaveLength(1);
  });
  it("affiche un état vide sans statistiques inventées", () => {
    const wrapper = mount(LoadState, {
      props: { empty: true, emptyText: "Aucun modèle enregistré" },
      slots: { default: "99 %" },
      global,
    });
    expect(wrapper.text()).toContain("Aucun modèle enregistré");
    expect(wrapper.text()).not.toContain("99 %");
  });
  it("traduit le statut et conserve un texte accessible", () => {
    expect(
      mount(StatusBadge, { props: { status: "corrected" }, global }).text(),
    ).toBe("Corrigé");
  });
  it("édite une boîte au clavier et borne les coordonnées", async () => {
    const wrapper = mount(BoxEditor, {
      props: {
        modelValue: { x: 0, y: 0, w: 0.4, h: 0.4 },
        src: "/original.jpg",
      },
    });
    await wrapper
      .get('[aria-label="Éditeur de bounding box"]')
      .trigger("keydown", { key: "ArrowRight" });
    expect(wrapper.emitted("update:modelValue")?.[0]?.[0]).toMatchObject({
      x: 0.002,
      w: 0.4,
    });
    await wrapper.get('input[aria-label="Largeur"]').setValue("2");
    expect(wrapper.emitted("update:modelValue")?.at(-1)?.[0]).toMatchObject({
      w: 1,
    });
  });
  it("permet de dessiner sans dépendre de la résolution affichée", async () => {
    const wrapper = mount(BoxEditor, {
      props: { modelValue: { x: 0, y: 0, w: 1, h: 1 }, src: "/original.jpg" },
    });
    const surface = wrapper.get(".box-surface");
    vi.spyOn(surface.element, "getBoundingClientRect").mockReturnValue({
      left: 10,
      top: 20,
      width: 200,
      height: 100,
    } as DOMRect);
    Object.assign(surface.element, { setPointerCapture: vi.fn() });
    await surface.trigger("pointerdown", {
      clientX: 30,
      clientY: 30,
      pointerId: 1,
    });
    await surface.trigger("pointermove", {
      clientX: 130,
      clientY: 80,
      pointerId: 1,
    });
    expect(wrapper.emitted("update:modelValue")?.at(-1)?.[0]).toMatchObject({
      x: 0.1,
      y: 0.1,
      w: 0.5,
      h: 0.5,
    });
  });
  it("respecte le gel des annotations test", async () => {
    const wrapper = mount(BoxEditor, {
      props: {
        modelValue: { x: 0, y: 0, w: 1, h: 1 },
        src: "/original.jpg",
        disabled: true,
      },
    });
    await wrapper.get(".box-surface").trigger("keydown", { key: "ArrowRight" });
    expect(wrapper.emitted("update:modelValue")).toBeUndefined();
  });
  it("rend les métriques manquantes explicitement et la matrice enregistrée", () => {
    const wrapper = mount(MetricsPanel, {
      props: {
        metrics: {
          count: 2,
          accuracy: 0.5,
          macro_f1: 0.25,
          classes: ["renards", "geai"],
          confusion_matrix: [
            [1, 1],
            [0, 0],
          ],
        },
      },
    });
    expect(wrapper.text()).toContain("50.0 %");
    expect(wrapper.text()).toContain("renards → geai");
    expect(wrapper.findAll("tbody tr")).toHaveLength(2);
    expect(wrapper.text()).toContain("Métriques vidéo non disponibles");
  });
  it("transmet l’identité et les erreurs de validation API", async () => {
    auth.csrf = "test-csrf";
    const fetch = vi
      .fn()
      .mockResolvedValue(
        new Response(
          JSON.stringify({ detail: [{ msg: "Révision invalide" }] }),
          { status: 422 },
        ),
      );
    vi.stubGlobal("fetch", fetch);
    await expect(
      api("/review/samples/x/decisions", { method: "POST", body: "{}" }),
    ).rejects.toThrow("Révision invalide");
    expect(fetch.mock.calls[0][1].headers.get("X-Reviewer")).toBeNull();
    expect(fetch.mock.calls[0][1].headers.get("X-CSRF-Token")).toBe(
      "test-csrf",
    );
    expect(fetch.mock.calls[0][1].credentials).toBe("same-origin");
    await flushPromises();
    vi.unstubAllGlobals();
  });
});
