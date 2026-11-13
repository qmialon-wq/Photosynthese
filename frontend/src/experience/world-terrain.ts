import * as T from "three";
import { seededRandom, terrainY, riverX, riverWidth } from "./world-utils";
import { waterVertex, waterFragment } from "./shaders";
import { surfaceMaterial } from "./surface-material";
export function createTerrain(economy: boolean) {
  const terrain = new T.Group();
  terrain.name = "terrain";
  const geometry = new T.PlaneGeometry(
    700,
    1150,
    economy ? 40 : 72,
    economy ? 120 : 190,
  );
  geometry.rotateX(-Math.PI / 2);
  geometry.translate(0, 0, -470);
  const positions = geometry.attributes.position,
    colors: number[] = [],
    color = new T.Color(),
    random = seededRandom(45);
  for (let i = 0; i < positions.count; i++) {
    const x = positions.getX(i),
      z = positions.getZ(i),
      y = terrainY(x, z);
    positions.setY(i, y);
    const field = (Math.floor((x + 350) / 37) + Math.floor((-z + 30) / 42)) % 3;
    color.setHSL(
      0.22 + field * 0.012,
      0.22 + random() * 0.12,
      y < 0 ? 0.12 : 0.19 + field * 0.025 + random() * 0.025,
    );
    colors.push(color.r, color.g, color.b);
  }
  geometry.setAttribute("color", new T.Float32BufferAttribute(colors, 3));
  geometry.computeVertexNormals();
  const oldIndex = geometry.getIndex()!,
    retained: number[] = [];
  for (let i = 0; i < oldIndex.count; i += 3) {
    const indices = [
        oldIndex.getX(i),
        oldIndex.getX(i + 1),
        oldIndex.getX(i + 2),
      ],
      x = indices.reduce((sum, n) => sum + positions.getX(n), 0) / 3,
      z = indices.reduce((sum, n) => sum + positions.getZ(n), 0) / 3;
    if (!(z < -165 && z > -525 && Math.abs(x - riverX(z)) < riverWidth(z) + 9))
      retained.push(...indices);
  }
  geometry.setIndex(retained);
  terrain.add(
    new T.Mesh(
      geometry,
      Object.assign(surfaceMaterial("#ffffff", "ground", true), {
        side: T.DoubleSide,
      }),
    ),
  );
  const bankPositions: number[] = [],
    bankIndices: number[] = [],
    bankColors: number[] = [];
  for (let row = 0; row <= 180; row++) {
    const z = -165 - row * 2,
      center = riverX(z),
      width = riverWidth(z) + 22;
    for (let col = 0; col <= 40; col++) {
      const x = center - width + (col * width) / 20,
        y = terrainY(x, z);
      bankPositions.push(x, y, z);
      color.setHSL(0.24, 0.3, y < 0 ? 0.13 : 0.22);
      bankColors.push(color.r, color.g, color.b);
      if (row < 180 && col < 40) {
        const a = row * 41 + col;
        bankIndices.push(a, a + 41, a + 1, a + 1, a + 41, a + 42);
      }
    }
  }
  const bankGeo = new T.BufferGeometry();
  bankGeo.setAttribute(
    "position",
    new T.Float32BufferAttribute(bankPositions, 3),
  );
  bankGeo.setAttribute("color", new T.Float32BufferAttribute(bankColors, 3));
  bankGeo.setIndex(bankIndices);
  bankGeo.computeVertexNormals();
  terrain.add(
    new T.Mesh(
      bankGeo,
      Object.assign(surfaceMaterial("#ffffff", "ground", true), {
        side: T.DoubleSide,
      }),
    ),
  );
  const water = new T.Group();
  water.name = "water";
  const waterUniforms = {
    phase: { value: 0 },
    night: { value: 0 },
    coast: { value: 0 },
  };
  const material = new T.ShaderMaterial({
    uniforms: waterUniforms,
    vertexShader: waterVertex,
    fragmentShader: waterFragment,
    transparent: true,
    depthWrite: false,
    side: T.DoubleSide,
  });
  const ribbon = new T.BufferGeometry(),
    vertices: number[] = [],
    uv: number[] = [],
    indices: number[] = [];
  for (let i = 0; i <= 140; i++) {
    const z = -175 - i * 2.45,
      w = riverWidth(z);
    for (const side of [-1, 1]) {
      vertices.push(riverX(z) + side * w, 0, z);
      uv.push(side * 0.5 + 0.5, i / 140);
    }
    if (i < 140) {
      const a = i * 2;
      indices.push(a, a + 1, a + 2, a + 1, a + 3, a + 2);
    }
  }
  ribbon.setAttribute("position", new T.Float32BufferAttribute(vertices, 3));
  ribbon.setAttribute("uv", new T.Float32BufferAttribute(uv, 2));
  ribbon.setIndex(indices);
  ribbon.computeVertexNormals();
  water.add(new T.Mesh(ribbon, material));
  const oceanGeometry = new T.PlaneGeometry(700, 195, 1, 1);
  oceanGeometry.rotateX(-Math.PI / 2);
  oceanGeometry.translate(0, 0, -742.5);
  water.add(new T.Mesh(oceanGeometry, material));
  const cartography = new T.Group();
  cartography.name = "cartography";
  const mapPositions: number[] = [];
  for (let row = 0; row < 13; row++)
    for (let column = 0; column < 8; column++) {
      const x = -155 + column * 40,
        z = -100 - row * 42,
        jitter = 4 * Math.sin(row * 3 + column),
        corners = [
          [x, z],
          [x + 36, z + jitter],
          [x + 37 + jitter, z - 36],
          [x - 2, z - 37],
          [x, z],
        ];
      for (let i = 0; i < 4; i++) {
        const a = corners[i],
          b = corners[i + 1];
        for (let k = 0; k < 5; k++) {
          const t = k / 5,
            u = (k + 1) / 5;
          for (const f of [t, u]) {
            const px = a[0] + (b[0] - a[0]) * f,
              pz = a[1] + (b[1] - a[1]) * f;
            mapPositions.push(px, terrainY(px, pz) + 0.23, pz);
          }
        }
      }
    }
  // A route is traced on the actual world-space river curve, not a fabricated geographic dataset.
  for (let i = 0; i < 170; i++) {
    const z = -150 - i * 1.8;
    mapPositions.push(riverX(z), 0.25, z, riverX(z - 1.8), 0.25, z - 1.8);
  }
  const mapGeometry = new T.BufferGeometry();
  mapGeometry.setAttribute(
    "position",
    new T.Float32BufferAttribute(mapPositions, 3),
  );
  const lines = new T.LineSegments(
    mapGeometry,
    new T.LineBasicMaterial({ color: "#c4ef99" }),
  );
  cartography.add(lines);
  return {
    terrain,
    water,
    waterUniforms,
    cartography,
    mapGeometry,
    mapVertexCount: mapPositions.length / 3,
  };
}
