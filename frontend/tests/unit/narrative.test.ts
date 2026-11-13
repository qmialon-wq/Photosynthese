import { describe, expect, it } from "vitest";
import {
  activeChapters,
  cameraKeys,
  narrativeDuration,
} from "../../src/experience/config";
import { sampleCamera } from "../../src/experience/CameraController";
import { sceneAt } from "../../src/experience/SceneManager";
import {
  transitions,
  transitionProgress,
  transitionAt,
  sampleEffects,
  reducedProgress,
} from "../../src/experience/journey";
describe("continuous eight-environment journey", () => {
  it("provides eight scenes and seven contiguous normalized transitions", () => {
    expect(activeChapters).toHaveLength(8);
    expect(transitions).toHaveLength(7);
    expect(narrativeDuration).toBe(210);
    expect(sceneAt(0).chapter.id).toBe("forest");
    expect(sceneAt(1).chapter.id).toBe("night-forest");
    for (let i = 0; i < 6; i++) {
      expect(transitions[i].end).toBe(transitions[i + 1].start);
      expect(sampleCamera(transitionProgress(transitions[i].id, 1))).toEqual(
        sampleCamera(transitionProgress(transitions[i + 1].id, 0)),
      );
    }
  });
  it("samples all 35 acceptance poses without direction dependence or non-finite geometry", () => {
    for (const transition of transitions) {
      const poses = [0, 0.25, 0.5, 0.75, 1].map((p) =>
        sampleCamera(transitionProgress(transition.id, p)),
      );
      expect(
        [1, 0.75, 0.5, 0.25, 0]
          .map((p) => sampleCamera(transitionProgress(transition.id, p)))
          .reverse(),
      ).toEqual(poses);
      for (const pose of poses) {
        expect(pose.position.every(Number.isFinite)).toBe(true);
        expect(pose.target.every(Number.isFinite)).toBe(true);
        expect(pose.fov).toBeGreaterThan(54);
        expect(pose.fov).toBeLessThan(62);
      }
    }
    const middle = sampleCamera(transitionProgress("ascent", 0.5));
    expect(middle.position[1]).toBeGreaterThan(12);
    expect(middle.position[1]).toBeLessThan(34);
    expect(sampleCamera(0).position[1]).toBe(0.7);
    expect(sampleCamera(1).position[1]).toBe(2.5);
  });
  it("keeps velocity continuous at every camera key and never jumps over a frame", () => {
    for (const key of cameraKeys.slice(1, -1)) {
      const p = key.time / 210,
        e = 0.000001,
        a = sampleCamera(p - e),
        b = sampleCamera(p),
        c = sampleCamera(p + e);
      for (let axis = 0; axis < 3; axis++)
        expect((b.position[axis] - a.position[axis]) / e).toBeCloseTo(
          (c.position[axis] - b.position[axis]) / e,
          0,
        );
    }
    for (let i = 1; i <= 4000; i++) {
      const a = sampleCamera((i - 1) / 4000),
        b = sampleCamera(i / 4000);
      expect(
        Math.hypot(...b.position.map((n, k) => n - a.position[k])),
      ).toBeLessThan(0.5);
    }
  });
  it("crosses an actual water level, emerges, and restores day/night and logo effects on reversal", () => {
    expect(
      sampleEffects(transitionProgress("immersion", 0), 2.2).immersion,
    ).toBe(0);
    expect(
      sampleEffects(transitionProgress("immersion", 1), -5).immersion,
    ).toBe(1);
    expect(
      sampleEffects(transitionProgress("emergence", 1), 1.7).immersion,
    ).toBe(0);
    expect(sampleEffects(1, 2.5).night).toBe(1);
    expect(sampleEffects(1, 2.5).logo).toBe(1);
    expect(sampleEffects(0, 0.7).night).toBe(0);
    expect(reducedProgress(0.1)).toBeCloseTo(35 / 210);
    expect(transitionAt(-1).local).toBe(0);
    expect(transitionAt(2).local).toBe(1);
    expect(sampleCamera(NaN)).toEqual(sampleCamera(0));
  });
});
