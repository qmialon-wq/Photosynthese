import * as T from "three";
import { clone } from "three/addons/utils/SkeletonUtils.js";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import { loadSpatial, disposeModel } from "./spatial-resources";
import type { GLTF } from "three/addons/loaders/GLTFLoader.js";
import { terrainY } from "./world-utils";
import { smoothstep } from "./journey";

type Species = "buse" | "pigeon" | "sanglier" | "chevreuil" | "poisson";
export interface AnimalBox {
  id: string;
  label: string;
  x: number;
  y: number;
  width: number;
  height: number;
  opacity: number;
}
interface Placement {
  id: string;
  species: Species;
  position: [number, number, number];
  size: number;
  rotation: number;
  from: number;
  to: number;
  clip?: string;
}
export const animalPlacements: readonly Placement[] = [
  {
    id: "roe-forest",
    species: "chevreuil",
    position: [5, 0, -5],
    size: 2.3,
    rotation: -1,
    from: 0,
    to: 24,
    clip: "Eating",
  },
  {
    id: "boar-forest",
    species: "sanglier",
    position: [17, 0, -20],
    size: 2.4,
    rotation: 1.2,
    from: 0,
    to: 24,
  },
  {
    id: "pigeon-forest",
    species: "pigeon",
    position: [8, 0, 4],
    size: 0.8,
    rotation: -0.5,
    from: 0,
    to: 17,
  },
  {
    id: "buzzard-a",
    species: "buse",
    position: [21, 54, -126],
    size: 5,
    rotation: 0,
    from: 20,
    to: 53,
  },
  {
    id: "buzzard-b",
    species: "buse",
    position: [30, 68, -151],
    size: 4.2,
    rotation: 0.5,
    from: 20,
    to: 53,
  },
  {
    id: "fish-a",
    species: "poisson",
    position: [0, -4.6, -326],
    size: 1.3,
    rotation: 1.5,
    from: 77,
    to: 108,
  },
  {
    id: "fish-b",
    species: "poisson",
    position: [3, -3.4, -334],
    size: 1.1,
    rotation: -1.4,
    from: 77,
    to: 108,
  },
  {
    id: "fish-c",
    species: "poisson",
    position: [8, -5, -343],
    size: 1.3,
    rotation: 1.6,
    from: 77,
    to: 108,
  },
  {
    id: "roe-wetland",
    species: "chevreuil",
    position: [14, 0.6, -458],
    size: 2.1,
    rotation: -1.2,
    from: 110,
    to: 137,
    clip: "Idle",
  },
  {
    id: "pigeon-meadow-a",
    species: "pigeon",
    position: [15, 0, -580],
    size: 1.2,
    rotation: 1,
    from: 132,
    to: 164,
  },
  {
    id: "pigeon-meadow-b",
    species: "pigeon",
    position: [18, 0, -583],
    size: 1.1,
    rotation: -1,
    from: 132,
    to: 164,
  },
  {
    id: "roe-night",
    species: "chevreuil",
    position: [9, 0, -889],
    size: 2.2,
    rotation: -1,
    from: 198,
    to: 214,
    clip: "Idle",
  },
  {
    id: "boar-night",
    species: "sanglier",
    position: [15, 0, -899],
    size: 2.4,
    rotation: 1.2,
    from: 198,
    to: 214,
  },
];
const labels: Record<Species, string> = {
  buse: "Buse",
  pigeon: "Pigeon",
  sanglier: "Sanglier",
  chevreuil: "Chevreuil",
  poisson: "Poisson · espèce à confirmer",
};

/** Reject offscreen/behind-camera boxes; never clamp a detached label onto the viewport edge. */
export function projectAnimalBox(
  object: T.Object3D,
  camera: T.PerspectiveCamera,
) {
  object.updateWorldMatrix(true, true);
  const bounds = new T.Box3().setFromObject(object, true);
  if (bounds.isEmpty()) return undefined;
  const center = bounds.getCenter(new T.Vector3()).project(camera);
  if (center.z < -1 || center.z > 1) return undefined;
  const points = [];
  for (const x of [bounds.min.x, bounds.max.x])
    for (const y of [bounds.min.y, bounds.max.y])
      for (const z of [bounds.min.z, bounds.max.z])
        points.push(new T.Vector3(x, y, z).project(camera));
  const x = (Math.min(...points.map((p) => p.x)) + 1) / 2,
    y = (1 - Math.max(...points.map((p) => p.y))) / 2;
  const width =
    (Math.max(...points.map((p) => p.x)) -
      Math.min(...points.map((p) => p.x))) /
    2;
  const height =
    (Math.max(...points.map((p) => p.y)) -
      Math.min(...points.map((p) => p.y))) /
    2;
  return x < 0.01 ||
    y < 0.05 ||
    x + width > 0.99 ||
    y + height > 0.94 ||
    width < 0.009
    ? undefined
    : { x, y, width, height };
}

function mergeBird(model: GLTF) {
  model.scene.updateMatrixWorld(true);
  const root = new T.Group();
  for (const side of ["body", "L", "R"]) {
    const geometries: T.BufferGeometry[] = [];
    model.scene.traverse((object: any) => {
      if (!object.isMesh) return;
      const wing = /Wing|Feathers/.test(object.name),
        matches =
          side === "body" ? !wing : wing && object.name.endsWith("_" + side);
      if (!matches) return;
      const geometry = object.geometry
        .clone()
        .applyMatrix4(object.matrixWorld)
        .toNonIndexed();
      const c = /Head_Neck|Tail/.test(object.name)
          ? new T.Color("#78644b")
          : object.material.color || new T.Color("#866b43"),
        colors = new Float32Array(geometry.attributes.position.count * 3);
      for (let i = 0; i < colors.length; i += 3) {
        colors[i] = c.r;
        colors[i + 1] = c.g;
        colors[i + 2] = c.b;
      }
      geometry.setAttribute("color", new T.BufferAttribute(colors, 3));
      for (const name of Object.keys(geometry.attributes))
        if (!["position", "normal", "color"].includes(name))
          geometry.deleteAttribute(name);
      geometries.push(geometry);
    });
    if (geometries.length) {
      const mesh = new T.Mesh(
        mergeGeometries(geometries)!,
        new T.MeshStandardMaterial({
          vertexColors: true,
          roughness: 0.88,
          side: T.DoubleSide,
        }),
      );
      mesh.name = "wing-" + side;
      root.add(mesh);
      geometries.forEach((g) => g.dispose());
    }
  }
  disposeModel(model);
  model.scene = root as T.Group;
}

export function createFauna(
  signal: AbortSignal,
  changed: () => void,
  issue: (message: string) => void,
) {
  const group = new T.Group();
  group.name = "local-3d-fauna";
  const loaded = new Map<Species, GLTF>(),
    pending = new Map<Species, Promise<void>>(),
    failed = new Set<Species>();
  const actors = new Map<
    string,
    { root: T.Group; model: T.Object3D; mixer?: T.AnimationMixer }
  >();
  let current = 0,
    started = false;
  function wanted(species: Species) {
    return animalPlacements.some(
      (p) =>
        p.species === species && current >= p.from - 18 && current <= p.to + 18,
    );
  }
  async function ensure(time: number) {
    started = true;
    current = time;
    for (const species of [...loaded.keys()])
      if (!wanted(species)) {
        for (const p of animalPlacements.filter((p) => p.species === species)) {
          const actor = actors.get(p.id);
          if (!actor) continue;
          actor.mixer?.stopAllAction();
          actor.mixer?.uncacheRoot(actor.model);
          actor.model.traverse((o: any) => {
            if (o.isSkinnedMesh) o.skeleton.dispose();
          });
          group.remove(actor.root);
          actors.delete(p.id);
        }
        disposeModel(loaded.get(species)!);
        loaded.delete(species);
      }
    const tasks = [...new Set(animalPlacements.map((p) => p.species))]
      .filter((s) => wanted(s) && !loaded.has(s) && !failed.has(s))
      .map((species) => {
        if (!pending.has(species))
          pending.set(
            species,
            (async () => {
              try {
                const model = await loadSpatial(species, signal);
                if (species === "buse") mergeBird(model);
                if (!wanted(species) || signal.aborted) {
                  disposeModel(model);
                  return;
                }
                loaded.set(species, model);
                for (const p of animalPlacements.filter(
                  (p) => p.species === species,
                )) {
                  const instance = clone(model.scene),
                    normalized = new T.Group(),
                    root = new T.Group();
                  const bounds = new T.Box3().setFromObject(instance),
                    dimensions = bounds.getSize(new T.Vector3()),
                    center = bounds.getCenter(new T.Vector3());
                  const scale =
                    p.size / Math.max(dimensions.x, dimensions.y, dimensions.z);
                  instance.position.sub(
                    new T.Vector3(
                      center.x,
                      species === "buse" || species === "poisson"
                        ? center.y
                        : bounds.min.y,
                      center.z,
                    ),
                  );
                  normalized.add(instance);
                  normalized.scale.setScalar(scale);
                  root.add(normalized);
                  root.rotation.y = p.rotation;
                  group.add(root);
                  let mixer: T.AnimationMixer | undefined;
                  const clip = model.animations.find((c) => c.name === p.clip);
                  if (clip) {
                    mixer = new T.AnimationMixer(instance);
                    mixer.clipAction(clip).play();
                  }
                  actors.set(p.id, { root, model: instance, mixer });
                }
              } catch (error) {
                if (!signal.aborted) {
                  failed.add(species);
                  issue(String(error));
                }
              } finally {
                pending.delete(species);
                changed();
              }
            })(),
          );
        return pending.get(species)!;
      });
    await Promise.all(tasks);
  }
  function apply(
    time: number,
    camera: T.PerspectiveCamera,
    enabled: boolean,
    immersion: number,
  ): AnimalBox[] {
    if (!started) return [];
    void ensure(time);
    const boxes: AnimalBox[] = [];
    group.visible = enabled;
    for (const p of animalPlacements) {
      const actor = actors.get(p.id);
      if (!actor) continue;
      const opacity =
        (p.from === 0 ? 1 : smoothstep(p.from, p.from + 2, time)) *
        (1 - smoothstep(p.to - 2, p.to, time));
      actor.root.visible =
        enabled &&
        opacity > 0.01 &&
        (p.species !== "poisson" || immersion > 0.5);
      if (!actor.root.visible) continue;
      const [x, y, z] = p.position,
        phase = time * 0.7 + p.id.length;
      actor.root.position.set(
        x,
        p.species === "buse" || p.species === "poisson"
          ? y
          : terrainY(x, z) + y,
        z,
      );
      if (p.species === "buse") {
        actor.root.position.x += Math.sin(phase * 0.27) * 5;
        actor.root.position.y += Math.cos(phase * 0.4) * 1.2;
        actor.root.rotation.z = Math.sin(phase * 0.27) * 0.13;
        actor.model.traverse((child) => {
          if (child.name === "wing-L")
            child.rotation.z = Math.sin(phase * 2.2) * 0.12;
          if (child.name === "wing-R")
            child.rotation.z = -Math.sin(phase * 2.2) * 0.12;
        });
      } else if (p.species === "poisson") {
        actor.root.position.x += Math.sin(phase * 0.5) * 0.6;
        actor.root.position.y += Math.sin(phase) * 0.15;
        actor.root.rotation.y = p.rotation + Math.cos(phase * 0.5) * 0.18;
      }
      actor.mixer?.setTime(time * 0.45);
      actor.root.updateWorldMatrix(true, true);
      const bounds = projectAnimalBox(actor.root, camera);
      if (bounds && opacity > 0.35)
        boxes.push({ id: p.id, label: labels[p.species], ...bounds, opacity });
    }
    return boxes;
  }
  return {
    group,
    ensure,
    apply,
    get pending() {
      return pending.size > 0;
    },
    dispose() {
      actors.forEach((actor) => {
        actor.mixer?.stopAllAction();
        actor.mixer?.uncacheRoot(actor.model);
        actor.model.traverse((o: any) => {
          if (o.isSkinnedMesh) o.skeleton.dispose();
        });
      });
      loaded.forEach(disposeModel);
      loaded.clear();
      actors.clear();
      group.clear();
    },
  };
}
