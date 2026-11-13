import * as T from "three";
import { chapterIds, type ChapterId } from "./config";
import { sampleEffects, smoothstep, type JourneyLayers } from "./journey";
import { createTerrain } from "./world-terrain";
import { createVegetation } from "./world-vegetation";
import { createCoast } from "./world-coast";
import { createObservation } from "./world-observation";
import { seededRandom, disposeScene } from "./world-utils";
import { skyVertex, skyFragment, fogVertex, fogFragment } from "./shaders";

export function createJourneyWorld(economy = false) {
  const scene = new T.Scene();
  scene.background = new T.Color("#233c32");
  const fog = new T.FogExp2("#92a58b", 0.007);
  scene.fog = fog;
  const ambient = new T.HemisphereLight("#dde6ed", "#1f291c", 2.6),
    sun = new T.DirectionalLight("#ffe6b5", 3.2);
  sun.position.set(-160, 210, 80);
  scene.add(ambient, sun);
  const terrain = createTerrain(economy),
    vegetation = createVegetation(economy),
    coast = createCoast(),
    observation = createObservation();
  scene.add(
    terrain.terrain,
    terrain.water,
    terrain.cartography,
    vegetation.group,
    coast.group,
    observation.group,
  );
  const atmosphere = new T.Group();
  atmosphere.name = "atmosphere";
  const skyUniforms = { night: { value: 0 }, coast: { value: 0 } };
  const sky = new T.Mesh(
    new T.SphereGeometry(900, 24, 16),
    new T.ShaderMaterial({
      uniforms: skyUniforms,
      vertexShader: skyVertex,
      fragmentShader: skyFragment,
      side: T.BackSide,
      depthWrite: false,
    }),
  );
  sky.renderOrder = -10;
  sky.frustumCulled = false;
  atmosphere.add(sky);
  const random = seededRandom(39),
    dummy = new T.Object3D();
  const cloudMaterial = new T.ShaderMaterial({
    uniforms: { night: { value: 0 } },
    transparent: true,
    depthWrite: false,
    vertexShader: `varying vec3 n;varying vec3 v;void main(){n=normalize(normalMatrix*transpose(inverse(mat3(instanceMatrix)))*normal);vec4 p=modelViewMatrix*instanceMatrix*vec4(position,1.);v=-p.xyz;gl_Position=projectionMatrix*p;}`,
    fragmentShader: `varying vec3 n;varying vec3 v;uniform float night;void main(){float facing=abs(dot(normalize(v),normalize(n)));float a=pow(facing,3.)*.28*exp(-length(v)*.0012)*(1.-night);vec3 c=mix(vec3(.5,.65,.63),vec3(.94,.96,.87),.5+.4*n.y);c=mix(c,vec3(.08,.14,.16),night);gl_FragColor=vec4(c,a);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
    }`,
  });
  const clouds = new T.InstancedMesh(
    new T.SphereGeometry(1, 24, 16),
    cloudMaterial,
    economy ? 35 : 70,
  );
  for (let i = 0; i < clouds.count; i++) {
    const group = Math.floor(i / 7);
    dummy.position.set(
      -150 + (group % 4) * 75 + random() * 15,
      75 + random() * 18,
      -130 - Math.floor(group / 4) * 190 - random() * 35,
    );
    dummy.rotation.set(0, random() * 6, 0);
    dummy.scale.set(13 + random() * 14, 3 + random() * 5, 8 + random() * 12);
    dummy.updateMatrix();
    clouds.setMatrixAt(i, dummy.matrix);
  }
  atmosphere.add(clouds);
  const fogMaterial = new T.ShaderMaterial({
    uniforms: { strength: { value: 1 } },
    vertexShader: fogVertex,
    fragmentShader: fogFragment,
    transparent: true,
    depthWrite: false,
    side: T.DoubleSide,
  });
  for (const z of [-30, -440, -470, -895]) {
    const plane = new T.Mesh(new T.PlaneGeometry(160, 10), fogMaterial);
    plane.position.set(0, 4, z);
    atmosphere.add(plane);
  }
  scene.add(atmosphere);
  const points = new T.Group();
  points.name = "particles";
  const bubbleGeometry = new T.BufferGeometry(),
    bubblePositions: number[] = [];
  for (let i = 0; i < 100; i++)
    bubblePositions.push((random() - 0.5) * 11, random(), -372 - random() * 28);
  bubbleGeometry.setAttribute(
    "position",
    new T.Float32BufferAttribute(bubblePositions, 3),
  );
  const bubbleMaterial = new T.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    uniforms: { phase: { value: 0 }, strength: { value: 1 } },
    vertexShader: `uniform float phase;varying float visibility;void main(){vec3 p=position;float t=fract(p.y+phase*.07);p.y=-6.+t*7.5;p.x+=sin(t*6.28+position.z)*.2;visibility=sin(t*3.14159);vec4 v=modelViewMatrix*vec4(p,1.);gl_Position=projectionMatrix*v;gl_PointSize=clamp(65./-v.z,1.,7.);}`,
    fragmentShader: `varying float visibility;uniform float strength;void main(){float d=length(gl_PointCoord-.5);float rim=smoothstep(.3,.4,d)*(1.-smoothstep(.4,.5,d));gl_FragColor=vec4(.7,.89,.81,rim*visibility*strength*.7);}`,
  });
  const bubbles = new T.Points(bubbleGeometry, bubbleMaterial);
  points.add(bubbles);
  const fish = new T.InstancedMesh(
    new T.ConeGeometry(0.2, 0.8, 5),
    new T.MeshStandardMaterial({
      color: "#75958a",
      roughness: 0.7,
      transparent: true,
      depthWrite: false,
    }),
    20,
  );
  for (let i = 0; i < fish.count; i++) {
    dummy.position.set(
      -14 + random() * 25,
      -1.5 - random() * 4,
      -285 - random() * 90,
    );
    dummy.rotation.set(0, random() * 6, Math.PI / 2);
    dummy.scale.set(1, 1, 0.3);
    dummy.updateMatrix();
    fish.setMatrixAt(i, dummy.matrix);
  }
  points.add(fish);
  const dataCount = 320,
    scatter: number[] = [],
    target: number[] = [],
    dataGeometry = new T.BufferGeometry();
  for (let i = 0; i < dataCount; i++) {
    scatter.push(
      (random() - 0.5) * 55,
      1 + random() * 24,
      -855 - random() * 60,
    );
    target.push((random() - 0.5) * 7, (random() - 0.5) * 2, 0);
  }
  dataGeometry.setAttribute(
    "position",
    new T.Float32BufferAttribute(scatter, 3),
  );
  const dataMaterial = new T.PointsMaterial({
    color: "#d5edb3",
    size: 0.075,
    transparent: true,
    opacity: 0.8,
    depthWrite: false,
    sizeAttenuation: true,
  });
  const data = new T.Points(dataGeometry, dataMaterial);
  data.frustumCulled = false;
  points.add(data);
  scene.add(points);
  const globalTarget = new T.Vector3();
  const dayFog = new T.Color("#92a58b"),
    coastFog = new T.Color("#b8c9c8"),
    waterFog = new T.Color("#174641"),
    nightFog = new T.Color("#142f36");
  const daySun = new T.Color("#ffe6b5"),
    nightSun = new T.Color("#a0c5d1");
  function attachTextures(textures: Map<string, T.Texture>) {
    for (const id of chapterIds) {
      const texture = textures.get(id);
      if (texture) vegetation.addTexture(id as ChapterId, texture);
    }
    const logo = textures.get("logo");
    if (!logo?.image) return;
    const image = logo.image as ImageBitmap,
      canvas = document.createElement("canvas");
    canvas.width = 240;
    canvas.height = 82;
    const ctx = canvas.getContext("2d")!;
    ctx.drawImage(image, 0, 0, 240, 82);
    const pixels = ctx.getImageData(0, 0, 240, 82).data,
      candidates: number[] = [];
    for (let y = 0; y < 82; y += 2)
      for (let x = 0; x < 240; x += 2)
        if (pixels[(y * 240 + x) * 4 + 3] > 180) candidates.push(x, y);
    for (let i = 0; i < dataCount && candidates.length; i++) {
      const p = Math.floor((random() * candidates.length) / 2) * 2;
      target[i * 3] = candidates[p] / 240 - 0.5;
      target[i * 3 + 1] = candidates[p + 1] / 82 - 0.5;
    }
  }
  function apply(
    progress: number,
    camera: T.PerspectiveCamera,
    layers: JourneyLayers,
  ) {
    const fx = sampleEffects(progress, camera.position.y),
      z = camera.position.z;
    terrain.terrain.visible = layers.terrain;
    // Enter the culling window while still extinguished by fog, before silhouettes can pop into view.
    coast.group.visible = layers.terrain && z < -350;
    terrain.water.visible = layers.water;
    vegetation.group.visible = layers.vegetation;
    vegetation.day.visible = z > -255;
    vegetation.hedges.visible = z < 100 && z > -780;
    vegetation.reeds.visible = z < -75 && z > -670;
    vegetation.kelp.visible = z > -520;
    vegetation.night.visible = z < -450;
    observation.group.visible = layers.observation;
    atmosphere.visible = layers.atmosphere;
    points.visible = layers.particles;
    bubbles.visible = layers.water && fx.immersion > 0;
    fish.visible = layers.water && fx.immersion > 0;
    (fish.material as T.MeshStandardMaterial).opacity = fx.immersion * 0.9;
    data.visible = fx.time > 187;
    dataMaterial.opacity = smoothstep(187, 198, fx.time) * 0.8;
    terrain.cartography.visible = layers.cartography && fx.map > 0.001;
    terrain.mapGeometry.setDrawRange(
      0,
      Math.floor((terrain.mapVertexCount * fx.map) / 2) * 2,
    );
    sky.position.copy(camera.position);
    skyUniforms.night.value = fx.night;
    const coastWeight =
      smoothstep(150, 175, fx.time) * (1 - smoothstep(187, 201, fx.time));
    skyUniforms.coast.value = coastWeight;
    clouds.visible = fx.night < 1;
    cloudMaterial.uniforms.night.value = fx.night;
    sun.color.copy(daySun).lerp(nightSun, fx.night);
    sun.intensity = T.MathUtils.lerp(2.5, 0.38, fx.night);
    ambient.intensity = T.MathUtils.lerp(1.65, 0.48, fx.night);
    fog.color
      .copy(dayFog)
      .lerp(coastFog, coastWeight)
      .lerp(waterFog, fx.immersion)
      .lerp(nightFog, fx.night);
    fog.density = layers.atmosphere
      ? T.MathUtils.lerp(
          T.MathUtils.lerp(0.007, 0.0038, coastWeight),
          0.042,
          fx.immersion,
        )
      : 0;
    fogMaterial.uniforms.strength.value = fx.night * 0.7 + 1;
    terrain.waterUniforms.night.value = fx.night;
    terrain.waterUniforms.coast.value = coastWeight;
    terrain.waterUniforms.phase.value = fx.time * 0.42;
    bubbleMaterial.uniforms.phase.value = fx.time;
    bubbleMaterial.uniforms.strength.value = layers.water ? fx.immersion : 0;
    const attributes = dataGeometry.attributes.position as T.BufferAttribute;
    const viewHeight = 2 * Math.tan((camera.fov * Math.PI) / 360) * 10,
      logoWidth = viewHeight * camera.aspect * 0.3;
    for (let i = 0; fx.time > 187 && i < dataCount; i++) {
      globalTarget
        .set(
          target[i * 3] * logoWidth + viewHeight * camera.aspect * 0.27,
          (target[i * 3 + 1] * logoWidth) / 2.926 + viewHeight * 0.16,
          -10,
        )
        .applyMatrix4(camera.matrixWorld);
      attributes.setXYZ(
        i,
        T.MathUtils.lerp(scatter[i * 3], globalTarget.x, fx.logo),
        T.MathUtils.lerp(scatter[i * 3 + 1], globalTarget.y, fx.logo),
        T.MathUtils.lerp(scatter[i * 3 + 2], globalTarget.z, fx.logo),
      );
    }
    attributes.needsUpdate = fx.time > 187;
    return { effects: fx, observationBounds: observation.screenBounds(camera) };
  }
  return {
    scene,
    apply,
    attachTextures,
    releaseTexture: vegetation.removeTexture,
    dispose: () => disposeScene(scene),
  };
}
export type JourneyWorld = ReturnType<typeof createJourneyWorld>;
