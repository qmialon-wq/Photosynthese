import * as T from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import {
  loadSpatial,
  disposeModel,
  spatialInventory,
} from "./spatial-resources";
import { woodlandPlacements, hedgerowPlacements } from "./woodland-layout";
import { seededRandom, riverX, riverWidth, terrainY } from "./world-utils";
import type { GLTF } from "three/addons/loaders/GLTFLoader.js";

export function createWoodland(signal: AbortSignal, economy: boolean) {
  const group = new T.Group();
  group.name = "textured-broadleaf-woodland";
  const bands: { group: T.Group; center: number; radius: number }[] = [];
  const models: GLTF[] = [],
    geometries: T.BufferGeometry[] = [];
  const cards: {
    mesh: T.InstancedMesh;
    locations: ReturnType<typeof woodlandPlacements>;
    slots: T.InstancedBufferAttribute;
    aspect: number;
  }[] = [];
  let atlas: T.Texture | undefined,
    cardMaterial: T.MeshBasicMaterial | undefined;
  async function load() {
    const [tree, grass, atlasResponse, metaResponse] = await Promise.all([
      loadSpatial("tree-near", signal),
      loadSpatial("grass-medium", signal),
      fetch(spatialInventory.assets["tree-atlas"].url, { signal }),
      fetch(spatialInventory.assets["tree-atlas-metadata"].url, { signal }),
    ]);
    models.push(tree, grass);
    if (!atlasResponse.ok || !metaResponse.ok)
      throw new Error("Woodland atlas unavailable");
    const bitmap = await createImageBitmap(await atlasResponse.blob());
    if (signal.aborted) {
      bitmap.close();
      return;
    }
    const { aspect } = await metaResponse.json();
    atlas = new T.Texture(bitmap);
    atlas.colorSpace = T.SRGBColorSpace;
    atlas.needsUpdate = true;
    atlas.anisotropy = 4;
    cardMaterial = new T.MeshBasicMaterial({
      map: atlas,
      alphaTest: 0.18,
      side: T.DoubleSide,
      fog: true,
    });
    cardMaterial.onBeforeCompile = (shader) => {
      shader.vertexShader = shader.vertexShader
        .replace(
          "#include <common>",
          "#include <common>\nattribute float viewSlot; varying float treeView;",
        )
        .replace(
          "#include <begin_vertex>",
          "#include <begin_vertex>\ntreeView=viewSlot;",
        );
      shader.fragmentShader = shader.fragmentShader
        .replace(
          "#include <common>",
          "#include <common>\nvarying float treeView;",
        )
        .replace(
          "#include <map_fragment>",
          `
      #ifdef USE_MAP
        float a=floor(treeView),b=mod(a+1.,4.),blend=smoothstep(0.,1.,fract(treeView));
        vec4 first=texture2D(map,vec2((vMapUv.x+a)*.25,1.-vMapUv.y));
        vec4 second=texture2D(map,vec2((vMapUv.x+b)*.25,1.-vMapUv.y));
        diffuseColor*=mix(first,second,blend);
      #endif`,
        );
    };
    tree.scene.updateMatrixWorld(true);
    const bounds = new T.Box3().setFromObject(tree.scene),
      treeHeight = bounds.max.y - bounds.min.y,
      centerX = (bounds.max.x + bounds.min.x) / 2,
      centerZ = (bounds.max.z + bounds.min.z) / 2;
    for (const center of [-25, -890]) {
      const sector = new T.Group();
      sector.name = `near-woodland-${center}`;
      const locations = [
        { x: -12, z: center + 25, height: 23, angle: 0.3, tint: 1 },
        { x: 14, z: center + 30, height: 24, angle: 2.3, tint: 1.06 },
        { x: -18, z: center - 13, height: 23, angle: 4.1, tint: 0.94 },
        { x: 18, z: center - 28, height: 25, angle: 5.4, tint: 1.02 },
      ].map((p) => ({ ...p, z: center < -800 ? Math.min(-880, p.z) : p.z }));
      tree.scene.traverse((object: any) => {
        if (!object.isMesh) return;
        const material = object.material as T.MeshStandardMaterial;
        material.transparent = false;
        material.alphaTest = 0;
        material.roughness = 0.9;
        material.envMapIntensity = 0.3;
        const mesh = new T.InstancedMesh(
          object.geometry,
          material,
          locations.length,
        );
        mesh.name = "near-broadleaf-" + object.name;
        mesh.castShadow = !economy;
        mesh.receiveShadow = true;
        locations.forEach((p, i) => {
          const dummy = new T.Object3D(),
            scale = p.height / treeHeight;
          dummy.position.set(p.x, terrainY(p.x, p.z), p.z);
          dummy.rotation.y = p.angle;
          dummy.scale.setScalar(scale);
          dummy.updateMatrix();
          mesh.setMatrixAt(
            i,
            dummy.matrix
              .clone()
              .multiply(
                new T.Matrix4().makeTranslation(
                  -centerX,
                  -bounds.min.y,
                  -centerZ,
                ),
              )
              .multiply(object.matrixWorld),
          );
          mesh.setColorAt(i, new T.Color(p.tint, p.tint, p.tint));
        });
        mesh.computeBoundingSphere();
        sector.add(mesh);
      });
      group.add(sector);
      bands.push({ group: sector, center, radius: 170 });
    }
    for (const [center, forest] of [
      [-65, true],
      [-935, true],
      [-170, false],
      [-270, false],
      [-430, false],
      [-555, false],
      [-625, false],
    ] as const) {
      const sector = new T.Group(),
        locations = woodlandPlacements(
          center,
          forest ? (economy ? 32 : 60) : economy ? 18 : 30,
          Math.abs(center) + 519,
          forest,
        );
      if (!forest) locations.push(...hedgerowPlacements(center));
      const geometry = new T.PlaneGeometry(1, 1);
      geometry.translate(0, 0.5, 0);
      geometries.push(geometry);
      const slots = new T.InstancedBufferAttribute(
        new Float32Array(locations.length),
        1,
      );
      geometry.setAttribute("viewSlot", slots);
      const mesh = new T.InstancedMesh(
        geometry,
        cardMaterial,
        locations.length,
      );
      mesh.name = "distant-baked-broadleaf";
      mesh.frustumCulled = false;
      cards.push({ mesh, locations, slots, aspect });
      sector.add(mesh);
      group.add(sector);
      bands.push({ group: sector, center, radius: forest ? 230 : 300 });
    }
    grass.scene.updateMatrixWorld(true);
    const byMaterial = new Map<T.Material, T.BufferGeometry[]>();
    let variant = 0;
    grass.scene.traverse((object: any) => {
      if (!object.isMesh) return;
      const geometry = object.geometry.clone().applyMatrix4(object.matrixWorld);
      geometry.computeBoundingBox();
      const center = geometry.boundingBox!.getCenter(new T.Vector3());
      geometry.translate(-center.x, -geometry.boundingBox!.min.y, -center.z);
      geometry.rotateY(variant++ * 2.4);
      for (const key of Object.keys(geometry.attributes))
        if (!["position", "normal", "uv"].includes(key))
          geometry.deleteAttribute(key);
      const list = byMaterial.get(object.material) || [];
      list.push(geometry);
      byMaterial.set(object.material, list);
    });
    for (const [material, pieces] of byMaterial) {
      const geometry = mergeGeometries(pieces)!;
      geometries.push(geometry);
      pieces.forEach((g) => g.dispose());
      const box = new T.Box3().setFromBufferAttribute(
          geometry.attributes.position as T.BufferAttribute,
        ),
        height = box.max.y - box.min.y;
      for (const center of [-4, -230, -445, -565, -885]) {
        const sector = new T.Group(),
          count = economy ? 12 : 24,
          random = seededRandom(Math.abs(center) + 50),
          mesh = new T.InstancedMesh(geometry, material, count);
        mesh.name = "textured-meadow-grasses";
        mesh.receiveShadow = true;
        for (let i = 0; i < count; i++) {
          const z = center + (random() - 0.5) * 35;
          let x = (i % 2 ? -1 : 1) * (3 + random() * 19);
          if (
            z < -165 &&
            z > -525 &&
            Math.abs(x - riverX(z)) < riverWidth(z) + 2
          )
            x += x < 0 ? -28 : 28;
          const dummy = new T.Object3D(),
            scale = (0.35 + random() * 0.4) / height;
          dummy.position.set(x, terrainY(x, z) - box.min.y * scale, z);
          dummy.rotation.y = random() * 6.28;
          dummy.scale.setScalar(scale);
          dummy.updateMatrix();
          mesh.setMatrixAt(i, dummy.matrix);
        }
        mesh.computeBoundingSphere();
        sector.add(mesh);
        group.add(sector);
        bands.push({ group: sector, center, radius: 95 });
      }
    }
  }
  const dummy = new T.Object3D();
  return {
    group,
    load,
    apply(camera: T.PerspectiveCamera, night: number) {
      bands.forEach(
        (b) =>
          (b.group.visible = Math.abs(camera.position.z - b.center) < b.radius),
      );
      if (cardMaterial) cardMaterial.color.setScalar(1 - night * 0.76);
      for (const { mesh, locations, slots, aspect } of cards) {
        if (!mesh.parent?.visible) continue;
        locations.forEach((p, i) => {
          const angle = Math.atan2(
            camera.position.x - p.x,
            camera.position.z - p.z,
          );
          dummy.position.set(p.x, terrainY(p.x, p.z), p.z);
          dummy.rotation.set(0, angle, 0);
          dummy.scale.set(p.height * aspect, p.height, 1);
          dummy.updateMatrix();
          mesh.setMatrixAt(i, dummy.matrix);
          slots.setX(i, ((((angle - p.angle) / (Math.PI / 2)) % 4) + 4) % 4);
        });
        mesh.instanceMatrix.needsUpdate = true;
        slots.needsUpdate = true;
      }
    },
    dispose() {
      group.traverse((o: any) => {
        if (o.isInstancedMesh) o.dispose();
      });
      group.clear();
      geometries.forEach((g) => g.dispose());
      cardMaterial?.dispose();
      atlas?.dispose();
      (atlas?.image as ImageBitmap)?.close?.();
      models.forEach(disposeModel);
    },
  };
}
