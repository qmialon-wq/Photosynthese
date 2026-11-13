<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import { gsap } from "gsap";
import { ACESFilmicToneMapping, PCFSoftShadowMap, WebGLRenderer } from "three";
import { CameraController } from "./CameraController";
import { AtmosphereController } from "./AtmosphereController";
import { AssetPreloader } from "./AssetPreloader";
import {
  PerformanceMonitor,
  type PerformanceSample,
} from "./PerformanceMonitor";
import { createWorld } from "./world";
import { RefractionPass } from "./RefractionPass";
import {
  defaultLayers,
  reducedProgress,
  transitionAt,
  type JourneyLayers,
} from "./journey";
import type { FrameReport } from "./telemetry";
import { pitchIndex } from "./pitch";
import { textureWindow } from "./runtime-assets";
const props = defineProps<{
  progress: number;
  reducedMotion: boolean;
  layers?: JourneyLayers;
  suspended?: boolean;
}>();
const emit = defineEmits<{
  ready: [];
  error: [message: string];
  performance: [sample: PerformanceSample];
  frame: [frame: FrameReport];
  assets: [issues: string[]];
}>();
const host = ref<HTMLDivElement>();
let renderFrame: (() => void) | undefined, teardown: (() => void) | undefined;
watch(
  () => [props.progress, props.reducedMotion, props.layers, props.suspended],
  () => renderFrame?.(),
  { flush: "post", deep: true },
);
onMounted(async () => {
  if (!host.value) return;
  const abort = new AbortController(),
    preloader = new AssetPreloader(),
    camera = new CameraController(),
    atmosphere = new AtmosphereController();
  let renderer: WebGLRenderer | undefined,
    world: ReturnType<typeof createWorld> | undefined,
    pass: RefractionPass | undefined,
    observer: ResizeObserver | undefined;
  let scheduled = false,
    dirty = false,
    initialized = false,
    renderCount = 0,
    device = "",
    quality: "standard" | "eco" = "standard",
    monitor: PerformanceMonitor;
  let assetVersion = 0,
    activeIndex = -1,
    assetsPending = true;
  const attached = new Set<string>();
  let wanted: string[] = [];
  async function selectAssets(index: number) {
    activeIndex = index;
    assetsPending = true;
    wanted = textureWindow(index);
    const version = ++assetVersion;
    const assets = await preloader.load(
      abort.signal,
      wanted.filter((id) => id !== "logo" || !attached.has("logo")),
    );
    if (abort.signal.aborted) return;
    if (version !== assetVersion) {
      preloader.releaseExcept([...new Set([...wanted, ...attached])]);
      return;
    }
    const additions = new Map(
      [...assets.textures].filter(([id]) => !attached.has(id)),
    );
    world!.attachTextures(additions);
    additions.forEach((texture, id) => {
      attached.add(id);
      if (id !== "logo") renderer!.initTexture(texture);
    });
    for (const id of attached)
      if (!wanted.includes(id)) {
        world!.releaseTexture(id);
        attached.delete(id);
      }
    // Logo pixels have been sampled into particle coordinates; no GPU texture or retained bitmap is needed.
    preloader.releaseExcept(wanted.filter((id) => id !== "logo"));
    emit("assets", assets.issues);
    assetsPending = false;
    invalidate();
  }
  function draw() {
    if (
      abort.signal.aborted ||
      !initialized ||
      document.hidden ||
      props.suspended ||
      !renderer ||
      !world ||
      !host.value
    )
      return;
    const began = performance.now();
    const index = pitchIndex(props.progress);
    if (index !== activeIndex) void selectAssets(index);
    renderer.info.reset();
    const progress = props.reducedMotion
        ? reducedProgress(props.progress)
        : props.progress,
      pose = camera.update(progress),
      layers = props.layers ?? defaultLayers;
    const state = world.apply(progress, camera.camera, layers);
    atmosphere.update(renderer, state.effects.night);
    world.renderReflection(renderer, camera.camera);
    pass!.render(
      renderer,
      world.scene,
      camera.camera,
      layers.water ? state.effects.immersion : 0,
      state.effects.time,
    );
    const rig = transitionAt(progress);
    const report: FrameReport = {
      progress,
      transition: rig.id,
      local: rig.local,
      position: [...pose.position],
      target: [...pose.target],
      fov: pose.fov,
      immersion: state.effects.immersion,
      night: state.effects.night,
      logo: state.effects.logo,
      observation: state.effects.observation,
      dataMorph: state.effects.dataMorph,
      bounds: state.observationBounds,
      drawCalls: renderer.info.render.calls,
      triangles: renderer.info.render.triangles,
      renderCount: ++renderCount,
      quality,
      pixelRatio: renderer.getPixelRatio(),
      renderer: device,
      textureCount: renderer.info.memory.textures,
      geometryCount: renderer.info.memory.geometries,
      residentImages: preloader.residentCount,
      estimatedImageBytes: preloader.estimatedImageBytes,
      postProcessing: layers.water && state.effects.immersion > 0,
      cpuSubmitMs: performance.now() - began,
      assetsPending: assetsPending || world.pending,
      animals: state.animals,
    };
    host.value.dataset.cameraY = pose.position[1].toFixed(3);
    host.value.dataset.progress = progress.toFixed(5);
    host.value.dataset.drawCalls = String(report.drawCalls);
    host.value.dataset.renderCount = String(renderCount);
    host.value.dataset.state = JSON.stringify(report);
    monitor.frame(performance.now(), !props.reducedMotion);
    emit("frame", report);
  }
  // Share the animation clock with the scroll timeline. Scheduling a second RAF
  // from Vue's post-flush watcher otherwise skips alternate GSAP frames.
  function tick() {
    if (!dirty || document.hidden || props.suspended) {
      stopRendering();
      return;
    }
    dirty = false;
    draw();
  }
  function stopRendering() {
    gsap.ticker.remove(tick);
    scheduled = false;
    dirty = false;
  }
  function invalidate() {
    if (!initialized || document.hidden || props.suspended) return;
    dirty = true;
    if (!scheduled) {
      scheduled = true;
      gsap.ticker.add(tick);
    }
  }
  function resize() {
    if (!renderer || !host.value) return;
    const box = host.value.getBoundingClientRect();
    renderer.setSize(box.width, box.height, false);
    camera.resize(box.width, box.height);
    pass?.resize(
      box.width * renderer.getPixelRatio(),
      box.height * renderer.getPixelRatio(),
    );
    invalidate();
  }
  const lost = (event: Event) => {
    event.preventDefault();
    abort.abort();
    stopRendering();
    emit(
      "error",
      "Le contexte graphique a été interrompu. Le parcours reste disponible en version 2D simplifiée.",
    );
  };
  const visibility = () => {
    if (document.hidden) {
      stopRendering();
    } else invalidate();
  };
  teardown = () => {
    abort.abort();
    initialized = false;
    stopRendering();
    observer?.disconnect();
    document.removeEventListener("visibilitychange", visibility);
    renderer?.domElement.removeEventListener("webglcontextlost", lost);
    pass?.dispose();
    world?.dispose();
    preloader.dispose();
    renderer?.dispose();
    renderer?.forceContextLoss();
    renderer?.domElement.remove();
  };
  try {
    renderer = new WebGLRenderer({
      antialias: true,
      powerPreference: "default",
    });
    renderer.toneMapping = ACESFilmicToneMapping;
    renderer.info.autoReset = false;
    const gl = renderer.getContext(),
      debug = gl.getExtension("WEBGL_debug_renderer_info");
    device = debug
      ? String(gl.getParameter(debug.UNMASKED_RENDERER_WEBGL))
      : String(gl.getParameter(gl.RENDERER));
    // Measured SwiftShader delivery is below 10 FPS on the audit laptop.
    // A deliberately explicit diagnostic URL can still measure that renderer.
    if (
      /SwiftShader|llvmpipe|software/i.test(device) &&
      new URLSearchParams(location.search).get("render") !== "software"
    ) {
      teardown();
      emit(
        "error",
        "Le rendu graphique logiciel est trop lent pour ce voyage. Le parcours continue sans WebGL.",
      );
      return;
    }
    const economy =
      /SwiftShader|llvmpipe|software/i.test(device) ||
      window.matchMedia("(max-width: 600px)").matches;
    quality = economy ? "eco" : "standard";
    renderer.shadowMap.enabled = !economy; renderer.shadowMap.type = PCFSoftShadowMap; renderer.shadowMap.autoUpdate = false;
    renderer.setPixelRatio(economy ? 0.65 : Math.min(devicePixelRatio, 1.5));
    monitor = new PerformanceMonitor(
      (sample) => emit("performance", sample),
      () => {
        quality = "eco";
        world?.setEconomy(true); renderer!.shadowMap.enabled = false;
        renderer!.setPixelRatio(
          Math.max(0.5, renderer!.getPixelRatio() * 0.72),
        );
        resize();
      },
      quality,
    );
    renderer.domElement.setAttribute("aria-hidden", "true");
    renderer.domElement.addEventListener("webglcontextlost", lost);
    host.value.append(renderer.domElement);
    world = createWorld(economy, abort.signal, invalidate, (message) =>
      emit("assets", [message]),
    );
    pass = new RefractionPass();
    camera.update(props.progress);
    resize();
    await selectAssets(pitchIndex(props.progress));
    await world.loadInitial();
    world.prepareEnvironment(renderer);
    if (abort.signal.aborted) return;
    if (
      !(await preloader.prepare(
        renderer,
        world.scene,
        camera.camera,
        abort.signal,
      ))
    )
      return;
    initialized = true;
    renderFrame = invalidate;
    observer = new ResizeObserver(resize);
    observer.observe(host.value);
    document.addEventListener("visibilitychange", visibility);
    renderer.info.reset();
    invalidate();
    emit("ready");
  } catch {
    const interrupted = abort.signal.aborted;
    teardown();
    if (!interrupted)
      emit(
        "error",
        "La vue WebGL n’est pas disponible. Le parcours est présenté en version 2D simplifiée.",
      );
  }
});
onBeforeUnmount(() => {
  renderFrame = undefined;
  teardown?.();
});
</script>
<template>
  <div
    ref="host"
    class="sx-canvas"
    aria-hidden="true"
    data-testid="experience-canvas"
  />
</template>
