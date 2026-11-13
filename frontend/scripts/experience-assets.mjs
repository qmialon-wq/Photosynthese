import { createHash } from "node:crypto";
import { existsSync, readFileSync, statSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { inflateSync } from "node:zlib";

export const assetRoot = fileURLToPath(
  new URL("../public/experience-art/", import.meta.url),
);
const repositoryRoot = fileURLToPath(new URL("../../", import.meta.url));
const sha256 = (bytes) => createHash("sha256").update(bytes).digest("hex");
const insist = (condition, message) => {
  if (!condition) throw new Error(message);
};
const json = (value) => JSON.stringify(value, null, 2) + "\n";
const load = (file) => JSON.parse(readFileSync(file, "utf8"));

export function resourcePath(relative, root = assetRoot) {
  insist(
    typeof relative === "string" && !path.isAbsolute(relative),
    "Resource path must be relative",
  );
  const resolved = path.resolve(root, relative);
  insist(
    !path.relative(root, resolved).startsWith(".."),
    `Resource outside asset root: ${relative}`,
  );
  return resolved;
}

/** Inspect real PNG pixels. Presence of an alpha channel alone is not transparency. */
export function inspectPng(bytes) {
  insist(
    bytes.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])),
    "Invalid PNG signature",
  );
  const width = bytes.readUInt32BE(16),
    height = bytes.readUInt32BE(20),
    bitDepth = bytes[24],
    colorType = bytes[25];
  let alpha = null;
  if (colorType === 6 || colorType === 4) {
    insist(
      bitDepth === 8 && bytes[28] === 0,
      "Alpha inspector requires non-interlaced 8-bit PNG",
    );
    const channels = colorType === 6 ? 4 : 2,
      stride = width * channels,
      chunks = [];
    for (let offset = 8; offset < bytes.length; ) {
      const size = bytes.readUInt32BE(offset),
        type = bytes.toString("ascii", offset + 4, offset + 8);
      if (type === "IDAT")
        chunks.push(bytes.subarray(offset + 8, offset + 8 + size));
      offset += size + 12;
    }
    const raw = inflateSync(Buffer.concat(chunks));
    insist(
      raw.length === (stride + 1) * height,
      "Unexpected PNG scanline size",
    );
    let previous = Buffer.alloc(stride),
      minimum = 255,
      maximum = 0,
      transparent = 0;
    const paeth = (a, b, c) => {
      const p = a + b - c,
        pa = Math.abs(p - a),
        pb = Math.abs(p - b),
        pc = Math.abs(p - c);
      return pa <= pb && pa <= pc ? a : pb <= pc ? b : c;
    };
    for (let y = 0; y < height; y++) {
      const offset = y * (stride + 1),
        filter = raw[offset],
        row = Buffer.allocUnsafe(stride);
      insist(filter <= 4, "Invalid PNG filter");
      for (let x = 0; x < stride; x++) {
        const left = x >= channels ? row[x - channels] : 0,
          above = previous[x],
          corner = x >= channels ? previous[x - channels] : 0;
        const predictor =
          filter === 0
            ? 0
            : filter === 1
              ? left
              : filter === 2
                ? above
                : filter === 3
                  ? Math.floor((left + above) / 2)
                  : paeth(left, above, corner);
        row[x] = (raw[offset + 1 + x] + predictor) & 255;
        if (x % channels === channels - 1) {
          const value = row[x];
          minimum = Math.min(minimum, value);
          maximum = Math.max(maximum, value);
          if (value === 0) transparent++;
        }
      }
      previous = row;
    }
    alpha = {
      min: minimum,
      max: maximum,
      transparentPixelFraction: Number(
        (transparent / (width * height)).toFixed(4),
      ),
    };
  }
  return { dimensions: { width, height, bitDepth, colorType }, alpha };
}

export function verifyAssets({ refresh = false, root = assetRoot } = {}) {
  const manifestPath = path.join(root, "manifest.json"),
    manifest = load(manifestPath);
  const expected = [
    "forest",
    "sky",
    "rivers",
    "underwater",
    "wetland",
    "meadow",
    "coast",
    "night-forest",
  ];
  insist(
    JSON.stringify(manifest.scenes.map((scene) => scene.id)) ===
      JSON.stringify(expected),
    "Expected the eight ordered atmospheres",
  );
  insist(
    manifest.approval.transitionWorkAllowed === false &&
      manifest.approval.mainPlatesApproved === false &&
      manifest.approval.layeredScenesReady === false,
    "Visual development must not approve transitions automatically",
  );
  let cursor = 0,
    present = 0,
    missing = 0,
    totalBytes = 0;
  const seen = new Set();
  for (const scene of manifest.scenes) {
    insist(
      scene.time.start === cursor &&
        scene.time.end - scene.time.start === scene.time.duration,
      `Non-contiguous storyboard: ${scene.id}`,
    );
    cursor = scene.time.end;
    const missingBriefs = load(
      resourcePath(`${scene.id}/prompts/missing.json`, root),
    );
    for (const resource of scene.resources) {
      insist(
        !seen.has(resource.expectedPath),
        `Duplicate resource: ${resource.expectedPath}`,
      );
      seen.add(resource.expectedPath);
      const expectedFile = resourcePath(resource.expectedPath, root);
      if (
        refresh &&
        resource.role === "foreground" &&
        resource.status === "missing" &&
        existsSync(expectedFile)
      ) {
        const promptPath = `${scene.id}/prompts/foreground.txt`;
        insist(
          existsSync(resourcePath(promptPath, root)),
          "Foreground requires its generation prompt",
        );
        Object.assign(resource, {
          path: resource.expectedPath,
          status: "present-review-required",
          licenseId: "generated-openai",
          generation: {
            tool: "built-in-image_gen",
            date: "2026-11-12",
            model: "not-exposed-by-tool",
            source: `${scene.id}/primary-v1.png`,
            promptPath,
          },
          qualityNotes: [
            "Détourage génératif candidat : vérifier les franges sur fonds clair et sombre et l’alignement au fond reconstruit avant intégration.",
          ],
        });
      }
      if (resource.status === "missing") {
        missing++;
        insist(
          resource.path === null &&
            resource.sha256 === null &&
            resource.dimensions === null,
          `Missing asset has fabricated metadata: ${resource.expectedPath}`,
        );
        insist(
          !existsSync(expectedFile),
          `Unregistered asset exists: ${resource.expectedPath}`,
        );
        const brief = missingBriefs.resources.find(
          (item) => item.expectedPath === resource.expectedPath,
        );
        insist(
          brief?.status === "not-produced" && brief.prompt.length > 100,
          `Missing generation brief: ${resource.expectedPath}`,
        );
        continue;
      }
      insist(
        resource.status === "present-review-required" &&
          resource.path === resource.expectedPath,
        `Invalid resource state: ${resource.expectedPath}`,
      );
      const file = resourcePath(resource.path, root);
      insist(existsSync(file), `Declared asset absent: ${resource.path}`);
      const bytes = readFileSync(file),
        metadata = inspectPng(bytes),
        digest = sha256(bytes);
      insist(
        metadata.dimensions.width >= 1024 && metadata.dimensions.height >= 576,
        `Master too small: ${resource.path}`,
      );
      if (resource.kind === "image-alpha")
        insist(
          metadata.alpha?.min === 0 &&
            metadata.alpha.max === 255 &&
            metadata.alpha.transparentPixelFraction > 0.1,
          `No usable transparent region: ${resource.path}`,
        );
      insist(
        existsSync(resourcePath(resource.generation.promptPath, root)),
        `Exact prompt missing: ${resource.path}`,
      );
      if (refresh)
        Object.assign(resource, {
          bytes: bytes.length,
          sha256: digest,
          ...metadata,
        });
      else
        insist(
          resource.sha256 === digest &&
            resource.bytes === bytes.length &&
            JSON.stringify(resource.dimensions) ===
              JSON.stringify(metadata.dimensions) &&
            JSON.stringify(resource.alpha) === JSON.stringify(metadata.alpha),
          `Metadata drift: ${resource.path}; run assets:refresh after a reviewed replacement`,
        );
      present++;
      totalBytes += bytes.length;
    }
    if (refresh)
      writeFileSync(
        resourcePath(`${scene.id}/manifest.json`, root),
        json({
          schemaVersion: manifest.schemaVersion,
          project: manifest.project,
          licenses: manifest.licenses,
          ...scene,
        }),
      );
    else {
      const sceneManifest = load(
        resourcePath(`${scene.id}/manifest.json`, root),
      );
      insist(
        JSON.stringify(sceneManifest.resources) ===
          JSON.stringify(scene.resources),
        `Scene manifest drift: ${scene.id}`,
      );
    }
  }
  insist(
    cursor === 300 && manifest.timing.productVideoSeconds === 90,
    "Storyboard must preserve 5 minutes including 90 seconds of product video",
  );
  const original = readFileSync(
      path.join(repositoryRoot, manifest.brand.sourcePath),
    ),
    brand = readFileSync(resourcePath(manifest.brand.path, root));
  insist(original.equals(brand), "Official logo copy was modified");
  if (refresh) {
    manifest.brand.sha256 = sha256(brand);
    for (const source of manifest.sources)
      if (source.path) {
        const file = path.join(repositoryRoot, source.path);
        insist(existsSync(file), `Source absent: ${source.path}`);
        source.sha256 = sha256(readFileSync(file));
        source.bytes = statSync(file).size;
      }
    manifest.inventory = { produced: present, missing, totalBytes };
    writeFileSync(manifestPath, json(manifest));
  } else {
    insist(
      manifest.brand.sha256 === sha256(brand),
      "Logo fingerprint mismatch",
    );
    insist(
      manifest.inventory.produced === present &&
        manifest.inventory.missing === missing &&
        manifest.inventory.totalBytes === totalBytes,
      "Inventory totals drift",
    );
  }
  return {
    scenes: manifest.scenes.length,
    produced: present,
    missing,
    totalBytes,
    transitionWorkAllowed: manifest.approval.transitionWorkAllowed,
  };
}

if (
  process.argv[1] &&
  path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)
) {
  try {
    console.log(
      JSON.stringify(
        verifyAssets({ refresh: process.argv.includes("--refresh") }),
        null,
        2,
      ),
    );
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
