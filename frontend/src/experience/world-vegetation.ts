import * as T from "three";
import { seededRandom, terrainY, riverX, riverWidth } from "./world-utils";
import type { ChapterId } from "./config";
import { surfaceMaterial } from "./surface-material";

function photographicMaterial(texture: T.Texture, crop = false) {
  const material = new T.MeshBasicMaterial({
    map: texture,
    transparent: true,
    alphaTest: 0.015,
    depthWrite: false,
    side: T.DoubleSide,
  });
  material.onBeforeCompile = (shader) => {
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", "#include <common>\nvarying vec2 vEdgeUv;")
      .replace(
        "#include <uv_vertex>",
        `#include <uv_vertex>\nvEdgeUv=uv/${crop ? "vec2(.38,.42)" : "vec2(1.)"};`,
      );
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", "#include <common>\nvarying vec2 vEdgeUv;")
      .replace(
        "#include <map_fragment>",
        `#include <map_fragment>\nfloat edge=smoothstep(0.,.18,vEdgeUv.x)*(1.-smoothstep(.82,1.,vEdgeUv.x))*smoothstep(0.,.18,vEdgeUv.y)*(1.-smoothstep(.82,1.,vEdgeUv.y));${crop ? "edge*=1.-smoothstep(.25,.49,length((vEdgeUv-.5)*vec2(1.,.9)));" : ""}diffuseColor.a*=edge;`,
      );
  };
  material.customProgramCacheKey = () => `photographic-edge-${crop}`;
  return material;
}

function woodland(
  count: number,
  zMin: number,
  zMax: number,
  spread: number,
  seed: number,
  economy: boolean,
) {
  const group = new T.Group(),
    random = seededRandom(seed),
    dummy = new T.Object3D(),
    color = new T.Color();
  const trunkMaterial = surfaceMaterial("#82775c", "bark");
  const trunks = new T.InstancedMesh(
    new T.CylinderGeometry(0.3, 0.65, 1, 7),
    trunkMaterial,
    count,
  );
  const branches = new T.InstancedMesh(
    new T.CylinderGeometry(0.05, 0.18, 1, 5),
    trunkMaterial,
    count * 3,
  );
  const crownGeo = new T.SphereGeometry(1, economy ? 7 : 10, economy ? 5 : 7);
  const positions = crownGeo.attributes.position;
  for (let i = 0; i < positions.count; i++) {
    const x = positions.getX(i),
      y = positions.getY(i),
      z = positions.getZ(i),
      n = 1 + 0.12 * Math.sin(x * 17 + z * 8) * Math.cos(y * 11);
    positions.setXYZ(i, x * n, y * n, z * n);
  }
  crownGeo.computeVertexNormals();
  const crowns = new T.InstancedMesh(
    crownGeo,
    new T.MeshStandardMaterial({ color: "#849b58", roughness: 1 }),
    count * 5,
  );
  const foliageMatrices: T.Matrix4[] = [];
  for (let i = 0; i < count; i++) {
    let x = (random() - 0.5) * spread,
      z = zMin + random() * (zMax - zMin);
    const corridor = z > -100 ? 13 : z > -885 && z < -820 ? 19 : 8;
    if (Math.abs(x - 2) < corridor) x += x < 2 ? -corridor : corridor;
    if (Math.hypot(x - 14, z + 458) < 20) x += 38;
    if (z < -175 && z > -510 && Math.abs(x - riverX(z)) < riverWidth(z) + 5)
      x += x < 0 ? -35 : 35;
    const height = 17 + random() * 12,
      radius = 0.65 + random() * 0.8,
      y = terrainY(x, z);
    dummy.position.set(x, y + height * 0.5, z);
    dummy.rotation.set(0, random() * 3, 0);
    dummy.scale.set(radius, height, radius);
    dummy.updateMatrix();
    trunks.setMatrixAt(i, dummy.matrix);
    color.setHSL(0.14, 0.11, 0.34 + random() * 0.12);
    trunks.setColorAt(i, color);
    for (let j = 0; j < 3; j++) {
      const angle = j * 2.1 + random(),
        direction = new T.Vector3(Math.cos(angle) * 4, 5, Math.sin(angle) * 4);
      dummy.position.set(
        x + direction.x * 0.5,
        y + height * 0.67 + j,
        z + direction.z * 0.5,
      );
      dummy.quaternion.setFromUnitVectors(
        new T.Vector3(0, 1, 0),
        direction.clone().normalize(),
      );
      dummy.scale.set(radius, direction.length(), radius);
      dummy.updateMatrix();
      branches.setMatrixAt(i * 3 + j, dummy.matrix);
    }
    for (let j = 0; j < 5; j++) {
      const a = j * 2.4;
      dummy.position.set(
        x + Math.cos(a) * 2.3,
        y + height + random() * 2,
        z + Math.sin(a) * 2.3,
      );
      dummy.rotation.set(random() * 0.3, random() * 6, random() * 0.3);
      dummy.scale.set(
        3.3 + random() * 1.8,
        2.4 + random(),
        3.3 + random() * 1.8,
      );
      dummy.updateMatrix();
      crowns.setMatrixAt(i * 5 + j, dummy.matrix);
      color.setHSL(0.23 + random() * 0.025, 0.32, 0.16 + random() * 0.14);
      crowns.setColorAt(i * 5 + j, color);
      dummy.rotation.set(j % 3 === 0 ? -Math.PI / 2 : 0, a, 0);
      dummy.scale.set(12, 9, 1);
      dummy.updateMatrix();
      foliageMatrices.push(dummy.matrix.clone());
    }
  }
  crowns.name = "proxy-crowns";
  group.userData.foliageMatrices = foliageMatrices;
  group.add(trunks, branches, crowns);
  return group;
}

export function createVegetation(economy: boolean) {
  const group = new T.Group();
  group.name = "vegetation";
  const day = woodland(economy ? 55 : 100, -100, 40, 150, 26, economy);
  day.name = "forest";
  const night = woodland(economy ? 55 : 85, -1010, -833, 150, 26, economy);
  night.name = "night-forest";
  // Ground-scale undergrowth gives the opening an edge and avoids giant foreground ferns.
  const leafShape = new T.Shape();
  leafShape.moveTo(0, 0);
  leafShape.quadraticCurveTo(0.22, 0.6, 0, 1.15);
  leafShape.quadraticCurveTo(-0.13, 0.5, 0, 0);
  const undergrowthGeometry = new T.ShapeGeometry(leafShape, 4);
  const undergrowthMaterial = new T.MeshStandardMaterial({
    color: "#6e8750",
    roughness: 1,
    side: T.DoubleSide,
  });
  for (const [forest, center, seed] of [
    [day, 0, 19],
    [night, -875, 29],
  ] as const) {
    const count = economy ? 280 : 560,
      leaves = new T.InstancedMesh(
        undergrowthGeometry,
        undergrowthMaterial,
        count,
      );
    const plantRandom = seededRandom(seed),
      plant = new T.Object3D(),
      tint = new T.Color();
    for (let i = 0; i < count; i++) {
      let x = (plantRandom() - 0.5) * 54;
      if (Math.abs(x) < 5) x += x < 0 ? -5 : 5;
      const z = center + (plantRandom() - 0.5) * 55;
      plant.position.set(x, terrainY(x, z), z);
      plant.rotation.set(
        (plantRandom() - 0.5) * 0.5,
        plantRandom() * Math.PI * 2,
        (plantRandom() - 0.5) * 0.6,
      );
      const height = 0.35 + plantRandom() * 0.75;
      plant.scale.set(0.65 + plantRandom() * 0.7, height, 1);
      plant.updateMatrix();
      leaves.setMatrixAt(i, plant.matrix);
      tint.setHSL(
        0.22 + plantRandom() * 0.035,
        0.3,
        0.22 + plantRandom() * 0.16,
      );
      leaves.setColorAt(i, tint);
    }
    leaves.name = "ground-undergrowth";
    forest.add(leaves);
  }
  const hedges = woodland(economy ? 70 : 130, -650, -115, 340, 73, economy);
  hedges.name = "bocage";
  // Keep the hedge line coherent while avoiding hundreds of separate meshes.
  const hedgeGeo = new T.SphereGeometry(1, 6, 4),
    hedgeMaterial = new T.MeshStandardMaterial({
      color: "#466237",
      roughness: 1,
    });
  const hedgeCount = 220,
    hedge = new T.InstancedMesh(hedgeGeo, hedgeMaterial, hedgeCount),
    dummy = new T.Object3D(),
    random = seededRandom(44);
  hedge.name = "field-hedges";
  for (let i = 0; i < hedgeCount; i++) {
    const row = Math.floor(i / 22),
      column = i % 22,
      x = -150 + column * 14,
      z = -115 - row * 49;
    dummy.position.set(x, terrainY(x, z) + 1.7, z);
    dummy.rotation.set(0, random(), 0);
    const clearObservation =
      Math.hypot(x - 14, z + 458) < 20 ||
      (z < -165 && z > -525 && Math.abs(x - riverX(z)) < riverWidth(z) + 12);
    dummy.scale.set(
      clearObservation ? 0 : 8,
      clearObservation ? 0 : 2.3,
      clearObservation ? 0 : 2.2,
    );
    dummy.updateMatrix();
    hedge.setMatrixAt(i, dummy.matrix);
  }
  hedges.add(hedge);
  const reeds = new T.Group();
  reeds.name = "reeds";
  const reedCount = economy ? 400 : 1000,
    reed = new T.InstancedMesh(
      new T.CylinderGeometry(0.025, 0.045, 1, 4),
      new T.MeshStandardMaterial({ color: "#8b9a58", roughness: 1 }),
      reedCount,
    );
  for (let i = 0; i < reedCount; i++) {
    const z = -408 - random() * 90,
      side = random() > 0.5 ? 1 : -1,
      x = riverX(z) + side * (14 + random() * 23),
      height = 1.5 + random() * 2.5;
    dummy.position.set(x, height * 0.5 - 0.4, z);
    dummy.rotation.set(0, random() * 6, (random() - 0.5) * 0.18);
    dummy.scale.set(1, height, 1);
    dummy.updateMatrix();
    reed.setMatrixAt(i, dummy.matrix);
  }
  reeds.add(reed);
  const kelp = new T.Group();
  kelp.name = "kelp";
  const kelpGeo = new T.PlaneGeometry(0.7, 4, 2, 9),
    kp = kelpGeo.attributes.position;
  for (let i = 0; i < kp.count; i++) {
    const y = kp.getY(i);
    kp.setZ(i, Math.sin(y * 1.3) * 0.55);
    kp.setX(i, kp.getX(i) * (1 + 0.4 * Math.sin(y * 3)));
  }
  kelpGeo.computeVertexNormals();
  const blades = new T.InstancedMesh(
    kelpGeo,
    new T.MeshStandardMaterial({
      color: "#6e7740",
      side: T.DoubleSide,
      roughness: 1,
    }),
    economy ? 65 : 140,
  );
  for (let i = 0; i < blades.count; i++) {
    const z = -265 - random() * 125,
      x = riverX(z) + (random() - 0.5) * 34;
    dummy.position.set(x, -4.5, z);
    dummy.rotation.set(0, random() * 6, (random() - 0.5) * 0.4);
    dummy.scale.set(1, 0.7 + random() * 0.6, 1);
    dummy.updateMatrix();
    blades.setMatrixAt(i, dummy.matrix);
  }
  kelp.add(blades);
  group.add(day, hedges, reeds, kelp, night);
  const cards = new T.Group();
  cards.name = "photographic-foregrounds";
  group.add(cards);
  const attachedCards = new Map<string, T.Group>();
  function removeTexture(id: string) {
    const bundle = attachedCards.get(id);
    if (!bundle) return;
    bundle.traverse((object) => {
      if (!(object instanceof T.Mesh)) return;
      object.geometry.dispose();
      (object.material as T.Material).dispose();
    });
    cards.remove(bundle);
    attachedCards.delete(id);
  }
  const cardSpecs: Record<
    ChapterId,
    { position: [number, number, number]; width: number }[]
  > = {
    forest: [
      { position: [0, 2.2, 10], width: 8 },
      { position: [0, 3.5, -13], width: 14 },
    ],
    sky: [{ position: [0, 31, -34], width: 42 }],
    rivers: [{ position: [4, 3, -232], width: 25 }],
    underwater: [{ position: [-3, -3, -323], width: 24 }],
    wetland: [{ position: [-15, 3, -448], width: 22 }],
    meadow: [{ position: [-15, 6, -567], width: 35 }],
    coast: [{ position: [-65, 44.5, -758], width: 45 }],
    "night-forest": [{ position: [0, 5, -885], width: 25 }],
  };
  const addTexture = (id: ChapterId, texture: T.Texture) => {
    if (attachedCards.has(id)) return;
    const bundle = new T.Group();
    attachedCards.set(id, bundle);
    cards.add(bundle);
    for (const spec of cardSpecs[id]) {
      const plane = new T.Mesh(
        new T.PlaneGeometry(spec.width, (spec.width * 941) / 1672),
        photographicMaterial(texture),
      );
      plane.position.set(...spec.position);
      if (id === "coast") plane.rotation.x = -Math.PI / 2;
      plane.name = `alpha-${id}`;
      bundle.add(plane);
    }
    if (id === "sky")
      for (const forest of [day, hedges, night]) {
        const geometry = new T.PlaneGeometry(1, 1),
          uv = geometry.attributes.uv;
        for (let i = 0; i < uv.count; i++)
          uv.setXY(i, uv.getX(i) * 0.38, uv.getY(i) * 0.42);
        const matrices = forest.userData.foliageMatrices as T.Matrix4[];
        const leaves = new T.InstancedMesh(
          geometry,
          photographicMaterial(texture, true),
          matrices.length,
        );
        if (forest === night)
          (leaves.material as T.MeshBasicMaterial).color.set("#314a48");
        const proxy = forest.getObjectByName("proxy-crowns");
        if (proxy) proxy.visible = false;
        matrices.forEach((matrix, index) => leaves.setMatrixAt(index, matrix));
        forest.add(leaves);
      }
  };
  return {
    group,
    day,
    night,
    hedges,
    reeds,
    kelp,
    cards,
    addTexture,
    removeTexture,
  };
}
