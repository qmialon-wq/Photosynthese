import { expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import fixtureData from "../fixtures/territorial-design.json";
import ProjectAlternatives from "../../src/components/ProjectAlternatives.vue";
import type { TerritorialAnalysis } from "../../src/territorial-context";
const fixture = fixtureData as TerritorialAnalysis;
function render() {
  return mount(ProjectAlternatives, {
    props: {
      proposals: structuredClone(fixture.design_proposals),
      facts: fixture.facts,
      sources: fixture.sources,
    },
  });
}
it("présente projet initial, changements, justification et conditions pour les cinq interventions", () => {
  const wrapper = render();
  expect(wrapper.findAll(".design-project")).toHaveLength(5);
  expect(wrapper.findAll(".design-option")).toHaveLength(12);
  expect(wrapper.get('[aria-label="Parcours de conception"]').text()).toContain(
    "Projet initial",
  );
  for (const option of wrapper.findAll(".design-option")) {
    expect(option.text()).toContain("Ce que cela changerait au projet");
    expect(option.text()).toContain("Conditions d’applicabilité");
    expect(option.text()).toContain("Niveau de justification : Exploratoire");
    expect(option.text()).toContain("option conditionnelle");
    expect(option.text()).toContain(
      "ne dispose pas d’une justification scientifique qualifiée",
    );
  }
  expect(wrapper.text()).not.toContain(
    "Scientifiquement qualifié · sous conditions",
  );
  expect(wrapper.text()).toContain("Référence générale de conception");
  wrapper.unmount();
});
it("change les alternatives affichées quand les interventions de l’analyse changent", async () => {
  const wrapper = render();
  await wrapper.setProps({
    proposals: fixture.design_proposals!.filter(
      (item) => item.project_action === "outdoor_lighting",
    ),
  });
  expect(wrapper.find('[data-intervention="fencing"]').exists()).toBe(false);
  expect(wrapper.findAll(".design-option")).toHaveLength(3);
  expect(wrapper.text()).toContain("Réduire la durée de fonctionnement");
  await wrapper.setProps({
    proposals: fixture.design_proposals!.filter(
      (item) => item.project_action === "earthworks",
    ),
  });
  expect(wrapper.find('[data-intervention="outdoor_lighting"]').exists()).toBe(
    false,
  );
  expect(wrapper.findAll(".design-option")).toHaveLength(2);
  expect(wrapper.text()).toContain("Comparer une implantation différente");
  wrapper.unmount();
});
it("signale les anciennes analyses, les interventions absentes et les entrées obsolètes", async () => {
  const wrapper = render();
  await wrapper.setProps({ proposals: undefined });
  expect(wrapper.text()).toContain("Cette analyse historique");
  await wrapper.setProps({ proposals: [] });
  expect(wrapper.text()).toContain("Renseignez les interventions");
  await wrapper.setProps({
    proposals: fixture.design_proposals,
    obsolete: true,
  });
  expect(wrapper.text()).toContain(
    "Relancez l’analyse pour examiner le projet modifié",
  );
  wrapper.unmount();
});
it("garde le caractère conditionnel lorsqu’une alternative est scientifiquement qualifiée", () => {
  const proposals = structuredClone(fixture.design_proposals!);
  proposals[0].alternatives[0].justification = {
    level: "scientifically_qualified",
    reason: "Source synthétique examinée pour le test uniquement.",
  };
  const wrapper = mount(ProjectAlternatives, {
    props: {
      proposals: [proposals[0]],
      facts: fixture.facts,
      sources: fixture.sources,
    },
  });
  expect(wrapper.text()).toContain(
    "Scientifiquement qualifié · sous conditions",
  );
  expect(wrapper.get(".design-option").text()).toContain(
    "option conditionnelle",
  );
  expect(wrapper.get(".design-option").text()).toContain(
    "Conditions d’applicabilité",
  );
  wrapper.unmount();
});
