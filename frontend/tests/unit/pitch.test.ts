import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";
import { createHash } from "node:crypto";
import { resolve } from "node:path";
import {
  applicationUrl,
  localMediaUrl,
  pitchChapters,
  pitchDuration,
  pitchIndex,
  pitchSeconds,
  progressAtSeconds,
  chapterProgress,
  juryCoverage,
  clock,
} from "../../src/experience/pitch";
import { sources } from "../../src/experience/sources";
import evidence from "../../src/experience/content/territorial-evidence.json";
import { reducedProgress } from "../../src/experience/journey";
import { anchorTimes, narrativeDuration } from "../../src/experience/config";

describe("sourced five-minute presentation", () => {
  it("allocates exactly five minutes, including ninety seconds for the manually controlled demo", () => {
    expect(pitchDuration).toBe(300);
    expect(pitchChapters).toHaveLength(8);
    expect(pitchChapters.reduce((sum, c) => sum + c.duration, 0)).toBe(300);
    expect(pitchChapters[5]).toMatchObject({
      id: "meadow",
      start: 150,
      duration: 90,
    });
    for (const [index, chapter] of pitchChapters.entries()) {
      expect(chapter.start).toBe(
        pitchChapters.slice(0, index).reduce((sum, c) => sum + c.duration, 0),
      );
      expect(chapter.oral.length).toBeGreaterThan(100);
      expect(chapter.screen.length).toBeGreaterThan(0);
      expect(chapter.interaction.length).toBeGreaterThan(20);
      expect(chapter.transition.length).toBeGreaterThan(20);
      expect(
        sources.some((source) => chapter.sources.includes(source.id)),
      ).toBe(true);
      expect(
        chapter.sources.every((id) =>
          sources.some((source) => source.id === id),
        ),
      ).toBe(true);
    }
    const words = pitchChapters
      .filter((c) => c.id !== "meadow")
      .map((c) => c.oral)
      .join(" ")
      .split(/\s+/).length;
    expect(words / 3.5).toBeLessThan(130);
    expect(juryCoverage).toHaveLength(12);
    expect(pitchChapters[3].status).toBe("future");
    expect(pitchChapters[6].status).toBe("expected");
    expect(pitchChapters[7].message).toContain("Arden, Romain et Quentin");
  });
  it("maps every editorial second reversibly without altering the camera path", () => {
    for (let second = 0; second <= 300; second += 0.5) {
      expect(pitchSeconds(progressAtSeconds(second))).toBeCloseTo(second, 7);
    }
    for (let i = 0; i < 8; i++) {
      expect(pitchIndex(chapterProgress(i))).toBe(i);
      expect(reducedProgress(chapterProgress(i))).toBe(
        anchorTimes[i] / narrativeDuration,
      );
      expect(clock(pitchSeconds(chapterProgress(i)))).toBe(
        clock(pitchChapters[i].start),
      );
    }
    expect(pitchSeconds(NaN)).toBe(0);
    expect(pitchSeconds(2)).toBe(300);
    expect(progressAtSeconds(-30)).toBe(0);
    expect(pitchIndex(1)).toBe(7);
  });
  it("keeps the evidence visualization identical to the supplied real archives", () => {
    for (const record of evidence) {
      const bytes = readFileSync(resolve(process.cwd(), "..", record.archive));
      expect(createHash("sha256").update(bytes).digest("hex")).toBe(
        record.archive_sha256,
      );
      const archive = JSON.parse(gunzipSync(bytes).toString("utf8"));
      expect(record.mode).toBe("archive");
      expect(record.location).toEqual(archive.location);
      for (const layer of record.layers) {
        const original = archive.layers[layer.code];
        expect(layer.status).toBe(original.status);
        expect(layer.features).toEqual(
          original.features.map(
            ({ name, source_id }: { name: string; source_id: string }) => ({
              name,
              source_id,
            }),
          ),
        );
        expect(
          createHash("sha256").update(original.raw_response).digest("hex"),
        ).toBe(layer.sha256);
      }
    }
  });
  it("allows configurable login routes while rejecting unsafe links and remote media", () => {
    expect(applicationUrl("/inscription?origine=pitch")).toBe(
      "/inscription?origine=pitch",
    );
    expect(applicationUrl("https://symbiose.example/connexion")).toBe(
      "https://symbiose.example/connexion",
    );
    for (const input of [
      undefined,
      "javascript:alert(1)",
      "//elsewhere.test",
      "/\\evil.test",
      "data:text/html,hi",
    ])
      expect(applicationUrl(input)).toBe("/connexion");
    expect(localMediaUrl("/experience-media/demo.mp4")).toBe(
      "/experience-media/demo.mp4",
    );
    for (const input of [
      "https://elsewhere.test/demo.mp4",
      "//elsewhere.test/demo.mp4",
      "javascript:hi",
      "/\\evil",
    ])
      expect(localMediaUrl(input)).toBe("");
  });
});
