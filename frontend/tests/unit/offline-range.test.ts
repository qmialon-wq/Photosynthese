// @vitest-environment node
import { describe, expect, it } from "vitest";
import { rangeResponse } from "../../scripts/offline-range.mjs";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import path from "node:path";
import inventory from "../../src/experience/content/runtime-assets.json";
describe("offline video seeking", () => {
  it("serves bounded and suffix ranges, retaining the media type", async () => {
    for (const [range, content, expected] of [
      ["bytes=2-4", "234", "bytes 2-4/10"],
      ["bytes=7-", "789", "bytes 7-9/10"],
      ["bytes=-3", "789", "bytes 7-9/10"],
    ]) {
      const response = await rangeResponse(
        new Request("http://localhost/video", { headers: { Range: range } }),
        new Response("0123456789", {
          headers: { "Content-Type": "video/mp4" },
        }),
      );
      expect(response.status).toBe(206);
      expect(response.headers.get("Content-Range")).toBe(expected);
      expect(response.headers.get("Content-Type")).toBe("video/mp4");
      expect(await response.text()).toBe(content);
    }
  });
  it("rejects invalid ranges instead of returning a corrupt playable file", async () => {
    for (const range of [
      "bytes=50-100",
      "bytes=9-2",
      "bytes=",
      "bytes=0-1,4-5",
    ])
      expect(
        (
          await rangeResponse(
            new Request("http://localhost/video", {
              headers: { Range: range },
            }),
            new Response("0123456789"),
          )
        ).status,
      ).toBe(416);
  });
});
it("checks actual optimized files and distinguishes delivery copies from source masters", () => {
  expect(
    JSON.parse(
      readFileSync(
        path.resolve(
          process.cwd(),
          "public/experience-art/runtime-assets.json",
        ),
        "utf8",
      ),
    ),
  ).toEqual(inventory);
  const resources = [
    ...Object.values(inventory.scenes).flatMap((scene) => Object.values(scene)),
    inventory.poster,
  ];
  expect(resources).toHaveLength(17);
  for (const item of resources) {
    const bytes = readFileSync(
      path.resolve(process.cwd(), "public", item.url.slice(1)),
    );
    expect(bytes.length).toBe(item.bytes);
    expect(createHash("sha256").update(bytes).digest("hex")).toBe(item.sha256);
    expect(item.bytes).toBeLessThan(item.sourceBytes);
    expect(item.alphaExactAtDeliveryResolution).toBe(true);
  }
});
