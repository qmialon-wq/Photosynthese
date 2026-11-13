import * as T from "three";
import { TessellateModifier } from "three/addons/modifiers/TessellateModifier.js";
import { mergeVertices } from "three/addons/utils/BufferGeometryUtils.js";
import { surfaceMaterial } from "./surface-material";

function erosion(x: number, y: number, z: number) {
  return (
    Math.sin(x * 0.43 + y * 0.61 + z * 0.27) * 0.45 +
    Math.sin(x * 1.37 - y * 0.83 + z * 0.49) * 0.18 +
    Math.sin(x * 3.1 + y * 2.3 + z * 1.6) * 0.06
  );
}
function stone(geometry: T.BufferGeometry, detail = 2.8) {
  const original = geometry,
    subdivided = new TessellateModifier(detail, 5).modify(geometry);
  if (subdivided !== original) original.dispose();
  const p = subdivided.attributes.position,
    normal = subdivided.attributes.normal;
  for (let i = 0; i < p.count; i++) {
    const x = p.getX(i),
      y = p.getY(i),
      z = p.getZ(i),
      displacement = erosion(x, y, z);
    p.setXYZ(
      i,
      x + normal.getX(i) * displacement,
      y + normal.getY(i) * displacement * 0.5,
      z + normal.getZ(i) * displacement * 1.5,
    );
  }
  const result = mergeVertices(subdivided, 0.008);
  subdivided.dispose();
  result.computeVertexNormals();
  const uv: number[] = [],
    rp = result.attributes.position,
    rn = result.attributes.normal;
  for (let i = 0; i < rp.count; i++)
    uv.push(
      (Math.abs(rn.getZ(i)) > 0.45 ? rp.getX(i) : rp.getZ(i)) * 0.11,
      rp.getY(i) * 0.11,
    );
  result.setAttribute("uv", new T.Float32BufferAttribute(uv, 2));
  return result;
}
export function createCoast() {
  const group = new T.Group();
  group.name = "etretat-evocation";
  const chalk = surfaceMaterial("#edeee2", "chalk");
  const shape = new T.Shape();
  shape.moveTo(-47, -1);
  shape.lineTo(-47.5, 34);
  shape.bezierCurveTo(-46, 43, -39, 46, -32, 45.5);
  shape.bezierCurveTo(-18, 46, -10, 42, -5, 36);
  shape.bezierCurveTo(1, 28, 3, 13, 8, -1);
  shape.lineTo(1, -1);
  shape.lineTo(-1.4, 12);
  shape.bezierCurveTo(-3, 33, -24, 35, -28, 12);
  shape.lineTo(-29, -1);
  shape.closePath();
  const arch = new T.Mesh(
    stone(
      new T.ExtrudeGeometry(shape, {
        depth: 13,
        steps: 4,
        bevelEnabled: true,
        bevelThickness: 1,
        bevelSize: 1,
        bevelSegments: 3,
        curveSegments: 32,
      }),
    ),
    chalk,
  );
  arch.position.set(0, -0.6, -753);
  arch.name = "porte-d-aval";
  group.add(arch);
  const head = new T.BoxGeometry(140, 46, 125, 32, 20, 32),
    hp = head.attributes.position;
  for (let i = 0; i < hp.count; i++) {
    const x = hp.getX(i),
      y = hp.getY(i),
      z = hp.getZ(i),
      top = Math.max(0, y / 23);
    hp.setXYZ(
      i,
      x + Math.sin(z * 0.11) * 2 + erosion(x, y, z) * 0.6,
      y +
        top * (Math.sin(x * 0.055) * 1.8 + Math.sin(z * 0.13)) +
        erosion(x, y, z) * 0.2,
      z + Math.sin(x * 0.07) * 2.5 + erosion(x, y, z),
    );
  }
  const headland = new T.Mesh(stone(head, 4), chalk);
  headland.position.set(-114, 20.8, -805);
  group.add(headland);
  const profile = Array.from({ length: 25 }, (_, i) => {
    const y = i * 1.8;
    return new T.Vector2(
      Math.max(
        0.12,
        7.2 * Math.pow(1 - i / 25, 0.82) + Math.sin(y * 0.38) * 0.3,
      ),
      y,
    );
  });
  profile.push(new T.Vector2(0.01, 44.5));
  const needle = new T.Mesh(stone(new T.LatheGeometry(profile, 40), 2), chalk);
  needle.position.set(23, -0.9, -753);
  needle.rotation.z = 0.025;
  needle.name = "aiguille";
  group.add(needle);
  group.traverse((o) => {
    if (o instanceof T.Mesh) {
      o.castShadow = true;
      o.receiveShadow = true;
    }
  });
  return { group, arch, needle };
}
