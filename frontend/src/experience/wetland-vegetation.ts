import * as T from "three";
import { riverX, seededRandom, terrainY } from "./world-utils";

/** Actual meshes for bank grasses and submerged ribbon plants; no photograph pasted into tree crowns. */
export function createVegetation(economy: boolean) {
  const group = new T.Group();
  group.name = "vegetation";
  const day = new T.Group(),
    night = new T.Group(),
    hedges = new T.Group();
  day.name = "forest";
  night.name = "night-forest";
  hedges.name = "bocage";
  const random = seededRandom(44),
    dummy = new T.Object3D();
  const reeds = new T.Group();
  reeds.name = "reeds";
  const count = economy ? 360 : 700;
  const stalk = new T.InstancedMesh(
    new T.CylinderGeometry(0.012, 0.032, 1, 5),
    new T.MeshStandardMaterial({ color: "#78805a", roughness: 0.85 }),
    count,
  );
  const seedHead = new T.InstancedMesh(
    new T.CapsuleGeometry(0.045, 0.28, 2, 5),
    new T.MeshStandardMaterial({ color: "#5b4632", roughness: 1 }),
    count,
  );
  const bladeGeometry = new T.PlaneGeometry(0.12, 1.2, 1, 5);
  const bp = bladeGeometry.attributes.position;
  for (let i = 0; i < bp.count; i++) {
    const y = bp.getY(i);
    bp.setX(i, bp.getX(i) * Math.max(0.05, 1 - Math.pow(y / 0.6, 2)));
    bp.setZ(i, (y + 0.6) * (y + 0.6) * 0.2);
  }
  bladeGeometry.computeVertexNormals();
  const leaves = new T.InstancedMesh(
    bladeGeometry,
    new T.MeshStandardMaterial({
      color: "#8a975c",
      roughness: 0.82,
      side: T.DoubleSide,
    }),
    count * 2,
  );
  for (let i = 0; i < count; i++) {
    const z = -408 - random() * 90,
      side = i % 2 ? 1 : -1,
      x = riverX(z) + side * (18 + random() * 17),
      height = 0.9 + random() * 1.8;
    const y = Math.max(-0.65, terrainY(x, z));
    dummy.position.set(x, y + height * 0.5, z);
    dummy.rotation.set(
      (random() - 0.5) * 0.12,
      random() * 6,
      (random() - 0.5) * 0.2,
    );
    dummy.scale.set(1, height, 1);
    dummy.updateMatrix();
    stalk.setMatrixAt(i, dummy.matrix);
    dummy.position.y = y + height;
    dummy.scale.set(1, 0.7 + random() * 0.5, 1);
    dummy.updateMatrix();
    seedHead.setMatrixAt(i, dummy.matrix);
    for (let j = 0; j < 2; j++) {
      dummy.position.set(x, y + height * (0.25 + j * 0.3), z);
      dummy.rotation.set(0.7, random() * 6, 0.1);
      dummy.scale.set(0.6 + random() * 0.7, 0.5 + random() * 0.5, 1);
      dummy.updateMatrix();
      leaves.setMatrixAt(i * 2 + j, dummy.matrix);
    }
  }
  stalk.receiveShadow = leaves.receiveShadow = true;
  reeds.add(stalk, seedHead, leaves);
  const kelp = new T.Group();
  kelp.name = "kelp";
  const geometry = new T.PlaneGeometry(0.34, 2.5, 3, 12),
    p = geometry.attributes.position;
  for (let i = 0; i < p.count; i++) {
    const y = p.getY(i),
      taper = Math.sin(((y + 1.25) / 2.5) * Math.PI);
    p.setXYZ(i, p.getX(i) * (0.08 + taper), y, Math.sin(y * 2) * 0.23);
  }
  geometry.computeVertexNormals();
  const material = new T.MeshStandardMaterial({
    color: "#667a4b",
    roughness: 0.65,
    side: T.DoubleSide,
  });
  material.onBeforeCompile = (shader) => {
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", "#include <common>\nvarying vec2 plantUv;")
      .replace(
        "#include <begin_vertex>",
        "#include <begin_vertex>\nplantUv=uv;",
      );
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", "#include <common>\nvarying vec2 plantUv;")
      .replace(
        "#include <color_fragment>",
        "#include <color_fragment>\nfloat vein=pow(max(0.,1.-abs(plantUv.x-.5)*7.),5.);diffuseColor.rgb*=.7+.25*sin(plantUv.y*38.)+vein*.3;",
      );
  };
  const blades = new T.InstancedMesh(geometry, material, economy ? 90 : 170);
  for (let i = 0; i < blades.count; i++) {
    const z = -270 - random() * 120,
      x = riverX(z) + (random() - 0.5) * 26,
      h = 0.6 + random() * 0.8;
    dummy.position.set(x, terrainY(x, z) + 1.25 * h, z);
    dummy.rotation.set(0, random() * 6.28, (random() - 0.5) * 0.5);
    dummy.scale.set(0.6 + random() * 0.7, h, 1);
    dummy.updateMatrix();
    blades.setMatrixAt(i, dummy.matrix);
    blades.setColorAt(
      i,
      new T.Color().setHSL(0.2 + random() * 0.05, 0.2, 0.4 + random() * 0.2),
    );
  }
  kelp.add(blades);
  group.add(day, hedges, reeds, kelp, night);
  // The texture API remains available to the preloader, but 3D scenery no longer uses flat foreground plates.
  return {
    group,
    day,
    night,
    hedges,
    reeds,
    kelp,
    addTexture() {},
    removeTexture(_id: string) {},
  };
}
