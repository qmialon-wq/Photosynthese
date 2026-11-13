import { it, expect, vi } from "vitest";
import { gsap } from "gsap";
import { NarrativeTimeline } from "../../src/experience/NarrativeTimeline";
import { pitchSeconds, progressAtSeconds } from "../../src/experience/pitch";

it("runs one 300-second clock through chapters and resumes for the remaining time", () => {
  let cursor: any, options: any;
  const tween = { kill: vi.fn() };
  const spy = vi.spyOn(gsap, "to").mockImplementation(((c: any, o: any) => {
    cursor = c; options = o; return tween;
  }) as any);
  try {
    const timeline = Object.create(NarrativeTimeline.prototype) as any;
    Object.assign(timeline, { reduced: false, trigger: { progress: 0 }, onPause: vi.fn(), scrollTo: vi.fn(), snap: vi.fn() });
    timeline.playPresentation();
    expect(options.duration).toBe(300);
    expect(options.ease).toBe("none");
    for (const seconds of [35, 60, 115, 150, 200, 240, 299]) {
      cursor.seconds = seconds; options.onUpdate();
      expect(pitchSeconds(timeline.scrollTo.mock.calls.at(-1)[0])).toBeCloseTo(seconds);
      expect(tween.kill).not.toHaveBeenCalled();
    }
    options.onComplete();
    expect(timeline.snap).toHaveBeenCalledWith(1);
    timeline.trigger.progress = progressAtSeconds(150);
    timeline.playPresentation();
    expect(options.duration).toBe(150);
  } finally { spy.mockRestore(); }
});
