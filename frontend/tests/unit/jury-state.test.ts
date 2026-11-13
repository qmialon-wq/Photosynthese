import { describe, expect, it } from "vitest";
import {
  checkpointKey,
  ownsPresentationKey,
  readCheckpoint,
  saveCheckpoint,
} from "../../src/experience/jury-state";
describe("jury incident recovery", () => {
  it("keeps only a validated presentation checkpoint and survives unavailable storage", () => {
    const values = new Map<string, string>();
    const storage = {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => {
        values.set(key, value);
      },
    };
    expect(readCheckpoint(storage)).toBeUndefined();
    saveCheckpoint(0.4, "presentation", storage);
    expect(readCheckpoint(storage)).toEqual({
      version: 1,
      progress: 0.4,
      mode: "presentation",
    });
    for (const bad of [
      "bad",
      "null",
      '{"version":2,"progress":0.5,"mode":"presentation"}',
      '{"version":1,"progress":5,"mode":"presentation"}',
    ]) {
      values.set(checkpointKey, bad);
      expect(readCheckpoint(storage)).toBeUndefined();
    }
    const unavailable = {
      getItem: () => {
        throw new Error("blocked");
      },
      setItem: () => {
        throw new Error("blocked");
      },
    };
    expect(readCheckpoint(unavailable)).toBeUndefined();
    expect(() =>
      saveCheckpoint(0.4, "presentation", unavailable),
    ).not.toThrow();
  });
  it("gives native controls their keys while chapter arrows also work from buttons", () => {
    const key = (name: string, tag: string) => {
      const event = new KeyboardEvent("keydown", { key: name });
      Object.defineProperty(event, "target", {
        value: document.createElement(tag),
      });
      return event;
    };
    expect(ownsPresentationKey(key("ArrowRight", "button"))).toBe(true);
    expect(ownsPresentationKey(key(" ", "button"))).toBe(false);
    for (const tag of ["input", "select", "textarea", "video", "summary"])
      expect(ownsPresentationKey(key("ArrowRight", tag))).toBe(false);
    expect(ownsPresentationKey(key("Home", "main"))).toBe(true);
    expect(ownsPresentationKey(key("Tab", "main"))).toBe(false);
  });
});
