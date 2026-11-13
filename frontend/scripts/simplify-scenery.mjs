import { readFile, writeFile, mkdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { MeshoptSimplifier } from "meshoptimizer";

const root = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../..",
);
await MeshoptSimplifier.ready;
const folder = path.join(root, "output/symbiose/scenery-sources/tree_small_02");
const source = JSON.parse(
  await readFile(path.join(folder, "tree_small_02.gltf"), "utf8"),
);
const buffers = await Promise.all(
  source.buffers.map((b) => readFile(path.join(folder, b.uri))),
);
const components = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4 };
const types = {
  5126: [4, "getFloat32"],
  5125: [4, "getUint32"],
  5123: [2, "getUint16"],
  5121: [1, "getUint8"],
};
function decode(index) {
  const a = source.accessors[index],
    view = source.bufferViews[a.bufferView],
    buffer = buffers[view.buffer || 0];
  const [bytes, method] = types[a.componentType],
    count = components[a.type];
  const data = new DataView(
    buffer.buffer,
    buffer.byteOffset,
    buffer.byteLength,
  );
  const result = new Float32Array(a.count * count);
  for (let i = 0; i < a.count; i++)
    for (let j = 0; j < count; j++)
      result[i * count + j] = data[method](
        (view.byteOffset || 0) +
          (a.byteOffset || 0) +
          i * (view.byteStride || bytes * count) +
          j * bytes,
        true,
      );
  return result;
}
for (const [lod, budgets] of [
  ["near", [3600, 120000, 2400]],
  ["far", [1400, 8000, 1000]],
]) {
  const doc = structuredClone(source),
    chunks = [],
    views = [],
    accessors = [],
    report = [];
  let offset = 0;
  function store(array, type, componentType, min, max) {
    const bytes = Buffer.from(array.buffer, array.byteOffset, array.byteLength),
      aligned = (offset + 3) & ~3;
    if (aligned > offset) chunks.push(Buffer.alloc(aligned - offset));
    views.push({ buffer: 0, byteOffset: aligned, byteLength: bytes.length });
    chunks.push(bytes);
    offset = aligned + bytes.length;
    accessors.push({
      bufferView: views.length - 1,
      componentType,
      count: array.length / components[type],
      type,
      ...(min ? { min, max } : {}),
    });
    return accessors.length - 1;
  }
  for (const mesh of doc.meshes)
    for (const primitive of mesh.primitives) {
      const position = decode(primitive.attributes.POSITION),
        original = Uint32Array.from(decode(primitive.indices));
      const target = Math.min(original.length, budgets[primitive.material] * 3);
      const [reduced, error] =
        primitive.material === 1
          ? MeshoptSimplifier.simplifyWithAttributes(
              original,
              position,
              3,
              decode(primitive.attributes.TEXCOORD_0),
              2,
              [0.5, 0.5],
              null,
              target,
              0.025,
              [],
            )
          : MeshoptSimplifier.simplify(original, position, 3, target, 0.06, []);
      const used = [...new Set(reduced)],
        remap = new Map(used.map((old, i) => [old, i]));
      const attributes = {};
      for (const [name, index] of Object.entries(primitive.attributes)) {
        if (name.startsWith("COLOR") || name === "TANGENT") continue;
        const input = decode(index),
          a = source.accessors[index],
          width = components[a.type],
          result = new Float32Array(used.length * width);
        for (let i = 0; i < used.length; i++)
          for (let j = 0; j < width; j++)
            result[i * width + j] = input[used[i] * width + j];
        const min =
          name === "POSITION"
            ? [0, 1, 2].map((j) =>
                used.reduce(
                  (n, _, i) => Math.min(n, result[i * 3 + j]),
                  Infinity,
                ),
              )
            : undefined;
        const max =
          name === "POSITION"
            ? [0, 1, 2].map((j) =>
                used.reduce(
                  (n, _, i) => Math.max(n, result[i * 3 + j]),
                  -Infinity,
                ),
              )
            : undefined;
        attributes[name] = store(result, a.type, 5126, min, max);
      }
      primitive.attributes = attributes;
      primitive.indices = store(
        Uint32Array.from(reduced, (value) => remap.get(value)),
        "SCALAR",
        5125,
      );
      report.push({
        material: primitive.material,
        originalTriangles: original.length / 3,
        triangles: reduced.length / 3,
        error,
      });
    }
  doc.buffers = [{ uri: `tree-${lod}.bin`, byteLength: offset }];
  doc.bufferViews = views;
  doc.accessors = accessors;
  doc.materials[1].alphaMode = "OPAQUE";
  delete doc.materials[1].alphaCutoff;
  await mkdir(folder, { recursive: true });
  await writeFile(path.join(folder, `tree-${lod}.bin`), Buffer.concat(chunks));
  await writeFile(path.join(folder, `tree-${lod}.gltf`), JSON.stringify(doc));
  await writeFile(
    path.join(folder, `tree-${lod}-report.json`),
    JSON.stringify(report, null, 2),
  );
  console.log(lod, report);
}
