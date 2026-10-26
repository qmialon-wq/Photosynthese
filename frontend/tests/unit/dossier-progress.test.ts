import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import DossierProgress from "../../src/components/DossierProgress.vue";

describe("suivi de génération", () => {
  it("affiche les compteurs réels et les limites d’un ancien calcul", () => {
    const wrapper = mount(DossierProgress, {
      props: {
        progress: {
          phase: "reading",
          detailed_tracking: false,
          documents_started: 23,
          documents_total: 578,
          chunks_read: 900,
          chunks_total: 20332,
          current_document: "Article en cours",
          current_document_chunks_read: 44,
          pages_done: 0,
          pages_total: 4,
          elapsed_seconds: 7200,
          seconds_since_activity: 60,
          last_activity_at: "2026-10-26T12:00:00Z",
          recent: [],
        },
      },
    });
    expect(wrapper.text()).toContain("22 / 578");
    expect(wrapper.text()).toContain("900 / 20332");
    expect(wrapper.text()).toContain("2 h 0 min");
    expect(wrapper.text()).toContain("Article en cours");
    expect(wrapper.text()).toContain("dernière observée");
    expect(wrapper.find('[aria-current="step"]').text()).toContain(
      "Lecture du corpus",
    );
    expect(wrapper.find("progress").attributes("value")).toBe("900");
    wrapper.unmount();
  });
});
