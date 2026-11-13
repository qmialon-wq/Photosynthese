import * as T from "three";
export function seededRandom(seed = 26) {
  let state = seed;
  return () => {
    state = (state * 1664525 + 1013904223) >>> 0;
    return state / 4294967296;
  };
}
export function riverX(z: number) {
  return 8 * Math.sin((z + 210) * 0.025) + 6 * Math.cos((z + 210) * 0.012);
}
export function riverWidth(z: number) {
  const ease = (x: number) => {
    const t = Math.max(0, Math.min(1, x));
    return t * t * (3 - 2 * t);
  };
  return 8 + 14 * ease((-z - 245) / 45) + 4 * ease((-z - 385) / 35);
}
export function terrainY(x: number, z: number) {
  const rolling =
    z > -130 || z < -825
      ? 0.65 + 0.55 * Math.sin(x * 0.035) * Math.cos(z * 0.023)
      : Math.max(
          0.3,
          2.4 +
            2.1 * Math.sin(x * 0.025) * Math.cos(z * 0.02) +
            Math.sin(z * 0.014),
        );
  if (z < -660 && z > -900) {
    const shoreline = -850 + 8 * Math.sin(x * 0.03) + 3 * Math.sin(x * 0.073);
    const t = Math.min(1, Math.max(0, (shoreline - z) / 16));
    return -9 + (rolling + 9) * t * t * (3 - 2 * t);
  }
  if (z < -175 && z > -510) {
    const distance = Math.abs(x - riverX(z)),
      width = riverWidth(z);
    if (distance < width) {
      const ease = (v: number) => {
        const t = Math.max(0, Math.min(1, v));
        return t * t * (3 - 2 * t);
      };
      const depth =
        1.8 + 5.2 * ease((-z - 250) / 35) * (1 - ease((-z - 375) / 35));
      const bed = -depth + Math.pow(distance / width, 6) * (depth + 0.2);
      // A low marsh island supports the observed animal above the water plane.
      const island = 1 - ease((Math.hypot(x - 14, z + 458) - 2) / 5);
      return bed + (0.6 - bed) * island;
    }
    // Ease the banks into the hills instead of a vertical step at the waterline.
    const bankT = Math.min(1, Math.max(0, (distance - width) / 12));
    return 0.2 + (rolling - 0.2) * bankT * bankT * (3 - 2 * bankT);
  }
  return rolling;
}
export function cylinderBetween(
  a: T.Vector3,
  b: T.Vector3,
  radius: number,
  material: T.Material,
  sides = 7,
) {
  const mesh = new T.Mesh(
    new T.CylinderGeometry(radius * 0.65, radius, a.distanceTo(b), sides),
    material,
  );
  mesh.position.copy(a).add(b).multiplyScalar(0.5);
  mesh.quaternion.setFromUnitVectors(
    new T.Vector3(0, 1, 0),
    b.clone().sub(a).normalize(),
  );
  return mesh;
}
export function disposeScene(scene: T.Scene) {
  const geometries = new Set<T.BufferGeometry>(),
    materials = new Set<T.Material>(),
    textures = new Set<T.Texture>();
  scene.traverse((object) => {
    if (
      object instanceof T.Mesh ||
      object instanceof T.Points ||
      object instanceof T.Line
    ) {
      geometries.add(object.geometry);
      const list = Array.isArray(object.material)
        ? object.material
        : [object.material];
      list.forEach((material) => {
        materials.add(material);
        for (const value of Object.values(material))
          if (value instanceof T.Texture) textures.add(value);
      });
      if (object instanceof T.InstancedMesh) object.dispose();
    }
  });
  geometries.forEach((geometry) => geometry.dispose());
  materials.forEach((material) => material.dispose());
  textures.forEach((texture) => texture.dispose());
  scene.clear();
}
