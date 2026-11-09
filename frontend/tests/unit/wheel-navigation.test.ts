import { describe, expect, it } from "vitest";
import {
  ACTIVE_WHEEL_SLOT,
  symbioseNavigation,
  wheelSlot,
  wheelSlots,
} from "../../src/symbiose-navigation";

describe("roue de navigation Symbiose", () => {
  it("conserve exactement six rubriques dans l’ordre demandé", () => {
    expect(symbioseNavigation.map((item) => item.label)).toEqual([
      "Accueil",
      "Vidéothèque",
      "Mes dossiers",
      "Analyses",
      "Validation humaine",
      "Documents scientifiques",
    ]);
    expect(wheelSlots).toHaveLength(6);
    expect(ACTIVE_WHEEL_SLOT).toBe(3);
  });
  it.each(
    symbioseNavigation.map((item, active) => [item.label, active] as const),
  )(
    "place %s en quatrième position sans perdre l’ordre cyclique",
    (_label, active) => {
      const slots = symbioseNavigation.map((_, index) =>
        wheelSlot(index, active),
      );
      expect(new Set(slots).size).toBe(6);
      expect(slots[active]).toBe(3);
      const ordered = symbioseNavigation
        .map((item, index) => ({ ...item, slot: slots[index] }))
        .sort((a, b) => a.slot - b.slot);
      expect(ordered[3].label).toBe(symbioseNavigation[active].label);
      for (let index = 0; index < 6; index++) {
        expect(ordered[(index + 1) % 6].label).toBe(
          symbioseNavigation[
            (symbioseNavigation.findIndex(
              (item) => item.label === ordered[index].label,
            ) +
              1) %
              6
          ].label,
        );
      }
    },
  );
});
