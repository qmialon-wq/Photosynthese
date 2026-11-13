import * as T from "three";
import { sampleEffects, smoothstep, type JourneyLayers } from "./journey";
import { createTerrain } from "./world-terrain";
import { createVegetation } from "./world-vegetation";
import { createCoast } from "./world-coast";
import { createObservation } from "./world-observation";
import { seededRandom, disposeScene } from "./world-utils";
import { skyVertex, skyFragment, fogVertex, fogFragment } from "./shaders";
import { createFauna } from "./world-fauna";
import { createNature } from "./world-nature";
import { logoParticleTargets } from "./logo-particles";
import { PlanarWaterReflection } from "./PlanarWaterReflection";

export function createJourneyWorld(
  economy = false,
  signal = new AbortController().signal,
  changed = () => {},
  issue = (_message: string) => {},
) {
  const scene = new T.Scene();
  scene.background = new T.Color("#233c32");
  const fog = new T.FogExp2("#bfcac8", 0.0025);
  scene.fog = fog;
  const ambient = new T.HemisphereLight("#c6dce7", "#44382a", 0.95),
    sun = new T.DirectionalLight("#fff0d6", 3.1);
  const sunDirection = new T.Vector3(-0.42, 0.68, -0.6).normalize();
  const coastalSunDirection = new T.Vector3(0.25, 0.74, 0.62).normalize();
  const lightDirection = sunDirection.clone();
  sun.castShadow = !economy;
  sun.shadow.mapSize.set(1024, 1024);
  sun.shadow.camera.left = sun.shadow.camera.bottom = -48;
  sun.shadow.camera.right = sun.shadow.camera.top = 48;
  sun.shadow.camera.near = 1;
  sun.shadow.camera.far = 420;
  sun.shadow.bias = -0.0002;
  sun.shadow.normalBias = 0.045;
  scene.add(ambient, sun, sun.target);
  const terrain = createTerrain(economy),
    vegetation = createVegetation(economy),
    coast = createCoast(),
    observation = createObservation();
  const reflection = new PlanarWaterReflection(economy);
  terrain.waterUniforms.reflectionMap.value = reflection.texture;
  terrain.waterUniforms.reflectionMatrix.value = reflection.matrix;
  let environment: T.WebGLRenderTarget | undefined,
    shadowEnabled = !economy,
    shadowUpdate = true;
  const fauna = createFauna(signal, changed, issue),
    nature = createNature(signal, changed, issue, economy);
  observation.animal.visible = false;
  scene.add(fauna.group, nature.group);
  scene.add(
    terrain.terrain,
    terrain.water,
    vegetation.group,
    coast.group,
    observation.group,
  );
  const atmosphere = new T.Group();
  atmosphere.name = "atmosphere";
  const skyUniforms = {
    night: { value: 0 },
    coast: { value: 0 },
    sunDirection: { value: lightDirection },
  };
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
  const dataCount = 7200,
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
    color: "#f5f8ef",
    size: 0.018,
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
  const dayFog = new T.Color("#dce1d7"),
    coastFog = new T.Color("#e1e4e4"),
    waterFog = new T.Color("#174641"),
    nightFog = new T.Color("#142f36");
  const daySun = new T.Color("#fff0d6"),
    nightSun = new T.Color("#a0c5d1");
  let logoAspect = 2.926;
  function attachTextures(textures: Map<string, T.Texture>) {
    const logo = textures.get("logo");
    if (!logo?.image) return;
    const image = logo.image as ImageBitmap,
      canvas = document.createElement("canvas");
    logoAspect = image.width / image.height;
    canvas.width = 1200;
    canvas.height = Math.round(1200 / logoAspect);
    const ctx = canvas.getContext("2d")!;
    ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
    const candidates = logoParticleTargets(
      ctx.getImageData(0, 0, canvas.width, canvas.height).data,
      canvas.width,
      canvas.height,
      dataCount,
    );
    dataGeometry.setDrawRange(0, candidates.length / 2);
    for (let i = 0; i < candidates.length / 2; i++) {
      target[i * 3] = candidates[i * 2];
      target[i * 3 + 1] = candidates[i * 2 + 1];
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
    fish.visible = false; // Replaced by the supplied textured GLB fish.
    (fish.material as T.MeshStandardMaterial).opacity = fx.immersion * 0.9;
    data.visible = fx.logo > 0;
    dataMaterial.opacity = fx.logo * 0.8;
    sky.position.copy(camera.position);
    skyUniforms.night.value = fx.night;
    const coastWeight =
      smoothstep(150, 175, fx.time) * (1 - smoothstep(187, 201, fx.time));
    skyUniforms.coast.value = coastWeight;
    terrain.terrain.traverse((o) => {
      if (o instanceof T.Mesh)
        [o.material]
          .flat()
          .forEach((m) => (m.userData.coastalHaze.value = coastWeight));
    });
    clouds.visible = fx.night < 1;
    cloudMaterial.uniforms.night.value = fx.night;
    sun.color.copy(daySun).lerp(nightSun, fx.night);
    sun.intensity = T.MathUtils.lerp(3.1, 0.62, fx.night);
    ambient.intensity = T.MathUtils.lerp(0.95, 0.36, fx.night);
    sun.target.position.set(camera.position.x, 2, camera.position.z - 20);
    lightDirection
      .copy(sunDirection)
      .lerp(coastalSunDirection, coastWeight)
      .normalize();
    terrain.waterUniforms.sunDirection.value.copy(lightDirection);
    sun.position.copy(sun.target.position).addScaledVector(lightDirection, 200);
    sun.target.updateMatrixWorld();
    shadowUpdate =
      shadowEnabled && fx.immersion < 0.1 && camera.position.y < 110;
    sun.shadow.intensity = shadowUpdate ? 0.7 : 0;
    scene.environmentIntensity = T.MathUtils.lerp(0.35, 0.09, fx.night);
    fog.color
      .copy(dayFog)
      .lerp(coastFog, coastWeight)
      .lerp(waterFog, fx.immersion)
      .lerp(nightFog, fx.night);
    fog.density = layers.atmosphere
      ? T.MathUtils.lerp(
          T.MathUtils.lerp(
            (z > -150 || z < -825) && camera.position.y < 25 ? 0.009 : 0.0025,
            0.003,
            coastWeight,
          ),
          0.042,
          fx.immersion,
        )
      : 0;
    fogMaterial.uniforms.strength.value = fx.night * 0.7 + 1;
    terrain.waterUniforms.night.value = fx.night;
    terrain.waterUniforms.coast.value = coastWeight;
    terrain.waterUniforms.phase.value = fx.time * 0.42;
    terrain.waterUniforms.fogColor.value.copy(fog.color);
    terrain.waterUniforms.fogDensity.value = fog.density;
    bubbleMaterial.uniforms.phase.value = fx.time;
    bubbleMaterial.uniforms.strength.value = layers.water ? fx.immersion : 0;
    const attributes = dataGeometry.attributes.position as T.BufferAttribute;
    const viewHeight = 2 * Math.tan((camera.fov * Math.PI) / 360) * 10,
      logoWidth = viewHeight * camera.aspect * 0.3;
    for (let i = 0; fx.logo > 0 && i < dataCount; i++) {
      globalTarget
        .set(
          target[i * 3] * logoWidth + viewHeight * camera.aspect * 0.27,
          (target[i * 3 + 1] * logoWidth) / logoAspect + viewHeight * 0.16,
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
    attributes.needsUpdate = fx.logo > 0;
    nature.group.visible = layers.vegetation;
    nature.apply(camera, fx.night);
    const animals = fauna.apply(
      fx.time,
      camera,
      layers.observation,
      fx.immersion,
    );
    return {
      effects: fx,
      observationBounds: observation.screenBounds(camera),
      animals,
    };
  }
  return {
    scene,
    apply,
    get needsShadowUpdate() {
      return shadowUpdate;
    },
    setEconomy(value: boolean) {
      reflection.setEconomy(value);
      shadowEnabled = !value;
      sun.castShadow = !value;
      if (value) {
        sun.shadow.map?.dispose();
        sun.shadow.map = null;
      }
    },
    prepareEnvironment(renderer: T.WebGLRenderer) {
      const envScene = new T.Scene(),
        geometry = new T.SphereGeometry(30, 24, 16),
        material = (sky.material as T.ShaderMaterial).clone();
      envScene.add(new T.Mesh(geometry, material));
      const generator = new T.PMREMGenerator(renderer);
      environment = generator.fromScene(envScene, 0.02, 0.1, 100, {
        size: economy ? 64 : 128,
      });
      scene.environment = environment.texture;
      scene.environmentIntensity = 0.35;
      generator.dispose();
      geometry.dispose();
      material.dispose();
    },
    renderReflection(renderer: T.WebGLRenderer, camera: T.PerspectiveCamera) {
      renderer.shadowMap.needsUpdate = shadowUpdate;
      reflection.render(
        renderer,
        scene,
        camera,
        terrain.water,
        terrain.water.visible,
      );
      terrain.waterUniforms.reflectionEnabled.value = reflection.active ? 1 : 0;
    },
    attachTextures,
    releaseTexture: vegetation.removeTexture,
    loadInitial: () =>
      Promise.all([
        fauna.ensure(0),
        nature.load(terrain.terrain, vegetation.group, coast.group),
      ]),
    get pending() {
      return fauna.pending || nature.pending;
    },
    dispose: () => {
      fauna.dispose();
      nature.dispose();
      reflection.dispose();
      environment?.dispose();
      sun.shadow.map?.dispose();
      disposeScene(scene);
    },
  };
}
export type JourneyWorld = ReturnType<typeof createJourneyWorld>;
