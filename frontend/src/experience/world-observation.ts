import * as T from "three";
import { cylinderBetween } from "./world-utils";

export function createObservation() {
  const group = new T.Group();
  group.name = "illustrative-observation";
  const fur = new T.MeshStandardMaterial({ color: "#8d7552", roughness: 1 }),
    dark = new T.MeshStandardMaterial({ color: "#2e3125", roughness: 1 });
  const animal = new T.Group();
  animal.position.set(14, 0.6, -458);
  animal.rotation.y = -0.5;
  animal.name = "illustrative-roe-deer";
  function ellipsoid(
    x: number,
    y: number,
    z: number,
    sx: number,
    sy: number,
    sz: number,
    material: T.Material = fur,
  ) {
    const mesh = new T.Mesh(new T.SphereGeometry(1, 10, 7), material);
    mesh.position.set(x, y, z);
    mesh.scale.set(sx, sy, sz);
    animal.add(mesh);
    return mesh;
  }
  ellipsoid(0, 1.25, 0, 1, 0.48, 0.38);
  ellipsoid(0.95, 1.55, 0, 0.28, 0.62, 0.26);
  ellipsoid(1.2, 2, 0, 0.42, 0.25, 0.24);
  ellipsoid(1.48, 1.92, 0, 0.19, 0.14, 0.18, dark);
  for (const x of [-0.65, 0.6])
    for (const z of [-0.25, 0.25])
      animal.add(
        cylinderBetween(
          new T.Vector3(x, 1.1, z),
          new T.Vector3(x - 0.05, 0.05, z),
          0.065,
          fur,
        ),
      );
  for (const z of [-0.22, 0.22]) {
    const ear = ellipsoid(1.12, 2.35, z, 0.12, 0.35, 0.08);
    ear.rotation.z = -0.25;
  }
  ellipsoid(1.34, 2.08, 0.22, 0.04, 0.04, 0.025, dark);
  ellipsoid(-0.95, 1.4, 0, 0.15, 0.12, 0.16);
  group.add(animal);
  const frame = new T.Group();
  frame.position.set(11, -6, -325);
  const metal = new T.MeshStandardMaterial({
    color: "#536c64",
    roughness: 0.7,
  });
  for (const x of [-1, 1])
    frame.add(
      cylinderBetween(
        new T.Vector3(x, 0, 0),
        new T.Vector3(x, 1.4, 0),
        0.07,
        metal,
      ),
    );
  frame.add(
    cylinderBetween(
      new T.Vector3(-1, 1.4, 0),
      new T.Vector3(1, 1.4, 0),
      0.07,
      metal,
    ),
  );
  const camera = new T.Mesh(new T.BoxGeometry(0.8, 0.55, 0.5), metal);
  camera.position.set(-0.4, 1.7, 0);
  frame.add(camera);
  const hydrophone = new T.Mesh(
    new T.CylinderGeometry(0.12, 0.12, 0.65, 10),
    metal,
  );
  hydrophone.position.set(0.7, 1.9, 0);
  frame.add(hydrophone);
  frame.add(
    cylinderBetween(
      new T.Vector3(0.7, 2.2, 0),
      new T.Vector3(0.7, 6, 0),
      0.018,
      metal,
    ),
  );
  group.add(frame);
  const trap = new T.Mesh(new T.BoxGeometry(0.45, 0.6, 0.25), metal);
  trap.position.set(5.6, 1.5, -3);
  group.add(trap);
  const box = new T.Box3();
  function screenBounds(camera: T.Camera) {
    animal.updateWorldMatrix(true, true);
    box.setFromObject(animal);
    const min = new T.Vector2(1, 1),
      max = new T.Vector2(-1, -1);
    for (const x of [box.min.x, box.max.x])
      for (const y of [box.min.y, box.max.y])
        for (const z of [box.min.z, box.max.z]) {
          const v = new T.Vector3(x, y, z).project(camera);
          min.x = Math.min(min.x, v.x);
          min.y = Math.min(min.y, v.y);
          max.x = Math.max(max.x, v.x);
          max.y = Math.max(max.y, v.y);
        }
    return {
      x: (min.x + 1) / 2,
      y: (1 - max.y) / 2,
      width: (max.x - min.x) / 2,
      height: (max.y - min.y) / 2,
    };
  }
  return { group, animal, screenBounds };
}
