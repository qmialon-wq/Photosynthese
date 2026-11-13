import * as T from "three";
import { Reflector } from "three/addons/objects/Reflector.js";

/** One bounded shared planar reflection for both water bodies; never recurses into water. */
export class PlanarWaterReflection {
  private reflector: Reflector;
  readonly matrix = new T.Matrix4();
  active = false;
  constructor(private economy: boolean) {
    this.reflector = new Reflector(new T.PlaneGeometry(1, 1), {
      textureWidth: economy ? 256 : 768,
      textureHeight: economy ? 256 : 768,
      multisample: 0,
      clipBias: 0.003,
    });
    this.reflector.rotation.x = -Math.PI / 2;
    this.reflector.updateMatrixWorld();
  }
  get texture() {
    return this.reflector.getRenderTarget().texture;
  }
  render(
    renderer: T.WebGLRenderer,
    scene: T.Scene,
    camera: T.PerspectiveCamera,
    water: T.Group,
    enabled: boolean,
  ) {
    this.active =
      enabled &&
      !this.economy &&
      camera.position.y > 0.12 &&
      ((camera.position.z < -145 && camera.position.z > -540) ||
        (camera.position.z < -640 && camera.position.z > -830));
    if (!this.active) return;
    const visible = water.visible;
    water.visible = false;
    try {
      this.reflector.onBeforeRender(
        renderer,
        scene,
        camera,
        this.reflector.geometry,
        this.reflector.material as T.Material,
        null as any,
      );
      this.matrix
        .copy(
          (this.reflector.material as T.ShaderMaterial).uniforms.textureMatrix
            .value,
        )
        .multiply(this.reflector.matrixWorld.clone().invert());
    } finally {
      water.visible = visible;
    }
  }
  setEconomy(value: boolean) {
    this.economy = value;
    if (value) this.reflector.getRenderTarget().dispose();
  }
  dispose() {
    this.reflector.dispose();
    this.reflector.geometry.dispose();
  }
}
