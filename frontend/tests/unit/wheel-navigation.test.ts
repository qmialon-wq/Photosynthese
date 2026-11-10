import { describe, expect, it } from "vitest";
import {
  ACTIVE_WHEEL_SLOT,
  symbioseNavigation,
  wheelSlot,
  wheelSlots,
} from "../../src/symbiose-navigation";
import {
  createWheelMotion,
  nearestWheelTarget,
  sampleWheelMotion,
  wheelPose,
} from "../../src/components/symbiose/wheel-motion";

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

describe("mécanisme cyclique", () => {
  it("prend le chemin le plus court pour toutes les paires, y compris aux extrémités", () => {
    for (let from = -12; from <= 12; from++) {
      for (let index = 0; index < 6; index++) {
        const target = nearestWheelTarget(from, index);
        expect(Math.abs(target - from)).toBeLessThanOrEqual(3);
        expect(((target % 6) + 6) % 6).toBe(index);
      }
    }
    expect(nearestWheelTarget(5, 0)).toBe(6);
    expect(nearestWheelTarget(0, 5)).toBe(-1);
    expect(nearestWheelTarget(0, 3)).toBe(3);
    expect(nearestWheelTarget(3, 0)).toBe(6);
    expect(nearestWheelTarget(5.8, 0)).toBe(6);
  });

  it("préserve l'espacement commun et retrouve exactement les six emplacements", () => {
    for (let step = -180; step <= 180; step++) {
      const progression = step / 30;
      const poses = Array.from({ length: 6 }, (_, i) =>
        wheelPose(i, progression),
      );
      for (let index = 0; index < 6; index++) {
        const gap = (poses[(index + 1) % 6].slot - poses[index].slot + 6) % 6;
        expect(gap).toBeCloseTo(1, 10);
      }
    }
    for (let active = 0; active < 6; active++) {
      for (let index = 0; index < 6; index++) {
        const pose = wheelPose(index, active);
        expect(pose.x).toBe(wheelSlots[wheelSlot(index, active)].x);
        expect(pose.y).toBe(wheelSlots[wheelSlot(index, active)].y);
        expect(pose.opacity).toBe(1);
        expect(pose.engagement).toBe(index === active ? 1 : 0);
      }
    }
  });

  it("masque entièrement le raccord sans traverser le centre de l'arc", () => {
    const before = wheelPose(0, 3.5 - 0.00001);
    const after = wheelPose(0, 3.5 + 0.00001);
    expect(before.opacity).toBeLessThan(0.00001);
    expect(after.opacity).toBeLessThan(0.00001);
    expect(before.y).toBeLessThan(wheelSlots[0].y);
    expect(after.y).toBeGreaterThan(wheelSlots[5].y);
  });

  it.each([-3, -2, -1, 1, 2, 3])(
    "verrouille %i cran(s) après un dépassement discret",
    (target) => {
      const motion = createWheelMotion(0, 0, target);
      expect(motion.duration).toBeGreaterThanOrEqual(450);
      expect(motion.duration).toBeLessThanOrEqual(660);
      expect(sampleWheelMotion(motion, 0).velocity).toBe(0);
      const detent = sampleWheelMotion(motion, motion.driveDuration);
      expect(detent.position * Math.sign(target)).toBeGreaterThan(
        Math.abs(target),
      );
      expect(Math.abs(detent.position - target)).toBeLessThanOrEqual(0.0220001);
      expect(detent.velocity).toBeCloseTo(0, 10);
      expect(sampleWheelMotion(motion, motion.duration)).toEqual({
        position: target,
        velocity: 0,
        done: true,
      });
    },
  );

  it("reprend position et vitesse lors d'inversions rapides, puis respecte la dernière demande", () => {
    let motion = createWheelMotion(0, 0, 1);
    for (const requested of [5, 2, 0, 4, 3]) {
      const current = sampleWheelMotion(motion, 175);
      const target = nearestWheelTarget(current.position, requested);
      motion = createWheelMotion(current.position, current.velocity, target);
      expect(sampleWheelMotion(motion, 0)).toEqual({ ...current, done: false });
      const next = sampleWheelMotion(motion, 0.01);
      expect(Math.abs(next.position - current.position)).toBeLessThan(0.001);
      expect(Math.abs(next.velocity - current.velocity)).toBeLessThan(0.00001);
    }
    expect(((sampleWheelMotion(motion, 1000).position % 6) + 6) % 6).toBe(3);
  });
});
