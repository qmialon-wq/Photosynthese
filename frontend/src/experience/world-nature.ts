import * as T from "three";
import {
  loadSpatial,
  spatialInventory,
  disposeModel,
  type SpatialId,
} from "./spatial-resources";
import { seededRandom, terrainY } from "./world-utils";
import { createWoodland } from "./world-woodland";
import type { GLTF } from "three/addons/loaders/GLTFLoader.js";

export function createNature(
  signal: AbortSignal,
  changed: () => void,
  issue: (message: string) => void,
  economy: boolean,
) {
  const group = new T.Group();
  group.name = "polyhaven-cc0-nature";
  const woodland = createWoodland(signal, economy);
  group.add(woodland.group);
  const sectors = [new T.Group(), new T.Group()];
  group.add(...sectors);
  const templates: GLTF[] = [],
    textures: T.Texture[] = [];
  let pending = true;
  async function load(terrain: T.Group, vegetation: T.Group, coast: T.Group) {
    const jobs = (
      ["fern_02", "rock_moss_set_01", "tree_stump_01"] as const
    ).map(async (id, index) => {
      const model = await loadSpatial(id, signal);
      templates.push(model);
      model.scene.updateMatrixWorld(true);
      const bounds = new T.Box3().setFromObject(model.scene),
        size = bounds.getSize(new T.Vector3());
      const scale =
        (index === 0 ? 3.2 : index === 1 ? 3.2 : 2) /
        Math.max(size.x, size.y, size.z);
      const random = seededRandom(701 + index),
        count = index === 0 ? (economy ? 16 : 36) : 4;
      const placements: T.Matrix4[] = [];
      for (let i = 0; i < count; i++) {
        const night = i >= count / 2,
          z = (night ? -865 : -2) - random() * 55;
        const x = (i % 2 ? -1 : 1) * (5 + random() * 18);
        const o = new T.Object3D();
        o.position.set(x, terrainY(x, z) - bounds.min.y * scale, z);
        o.rotation.y = random() * Math.PI * 2;
        o.scale.setScalar(scale * (0.7 + random() * 0.6));
        o.updateMatrix();
        placements.push(o.matrix.clone());
      }
      model.scene.traverse((object: any) => {
        if (!object.isMesh) return;
        for (let sector = 0; sector < 2; sector++) {
          const mesh = new T.InstancedMesh(
            object.geometry,
            object.material,
            count / 2,
          );
          mesh.name = "polyhaven-" + id;
          for (let i = 0; i < count / 2; i++)
            mesh.setMatrixAt(
              i,
              placements[i + (sector * count) / 2]
                .clone()
                .multiply(object.matrixWorld),
            );
          mesh.computeBoundingSphere();
          sectors[sector].add(mesh);
        }
      });
    });
    jobs.push(woodland.load());
    jobs.push(
      (async () => {
        for (const [name, kind, root] of [
          ["forest_ground_04", "ground", terrain],
          ["rock_face_02", "chalk", coast],
        ] as const) {
          const maps = await Promise.all(
            (["Diffuse", "nor_gl", "Rough"] as const).map(async (type) => {
              const id = `${name}-${type}` as SpatialId;
              const response = await fetch(spatialInventory.assets[id].url, {
                signal,
              });
              if (!response.ok)
                throw new Error(`Matériau local indisponible : ${id}`);
              const bitmap = await createImageBitmap(await response.blob());
              if (signal.aborted) {
                bitmap.close();
                throw new DOMException("Aborted", "AbortError");
              }
              const texture = new T.Texture(bitmap);
              texture.wrapS = texture.wrapT = T.RepeatWrapping;
              texture.anisotropy = 4;
              texture.repeat.set(1, 1);
              if (type === "Diffuse") texture.colorSpace = T.SRGBColorSpace;
              texture.needsUpdate = true;
              textures.push(texture);
              return texture;
            }),
          );
          for (const materialRoot of kind === "ground" ? [root, coast] : [root])
            materialRoot.traverse((object: any) => {
              if (!object.isMesh) return;
              const materials = Array.isArray(object.material)
                ? object.material
                : [object.material];
              for (const material of materials)
                if (material.userData.surface === kind) {
                  material.map = maps[0];
                  material.normalMap = maps[1];
                  material.roughnessMap = maps[2];
                  material.normalScale.set(
                    kind === "chalk" ? 0.9 : 0.65,
                    kind === "chalk" ? 0.9 : 0.65,
                  );
                  material.needsUpdate = true;
                }
            });
        }
      })(),
    );
    await Promise.all(
      jobs.map((job) =>
        job.catch((error) => {
          if (!signal.aborted) issue(String(error));
        }),
      ),
    );
    const grass = await fetch(
      spatialInventory.assets["aerial_grass_rock-Diffuse"].url,
      { signal },
    );
    if (!grass.ok) throw new Error("Grass surface unavailable");
    const grassBitmap = await createImageBitmap(await grass.blob());
    if (signal.aborted) {
      grassBitmap.close();
      return;
    }
    const grassMap = new T.Texture(grassBitmap);
    grassMap.colorSpace = T.SRGBColorSpace;
    grassMap.wrapS = grassMap.wrapT = T.RepeatWrapping;
    grassMap.anisotropy = 4;
    grassMap.needsUpdate = true;
    textures.push(grassMap);
    for (const root of [terrain, coast])
      root.traverse((o: any) => {
        if (o.isMesh)
          for (const material of [o.material].flat())
            if (["ground", "chalk"].includes(material.userData.surface)) {
              material.userData.grassMap = grassMap;
              material.needsUpdate = true;
            }
      });
    pending = false;
    changed();
  }
  return {
    group,
    load,
    apply(camera: T.PerspectiveCamera, night: number) {
      const z = camera.position.z;
      woodland.apply(camera, night);
      sectors[0].visible = Math.abs(z + 25) < 145;
      sectors[1].visible = Math.abs(z + 890) < 145;
    },
    get pending() {
      return pending;
    },
    dispose() {
      woodland.dispose();
      group.traverse((object: any) => {
        if (object.isInstancedMesh) object.dispose();
      });
      group.clear();
      templates.forEach(disposeModel);
      textures.forEach((texture) => {
        texture.dispose();
        (texture.image as ImageBitmap).close?.();
      });
    },
  };
}
