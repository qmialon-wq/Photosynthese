import * as T from "three";
import { screenVertex, refractionFragment } from "./shaders";
export class RefractionPass {
  private target = new T.WebGLRenderTarget(1, 1, { depthBuffer: true });
  private scene = new T.Scene();
  private camera = new T.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  private material = new T.ShaderMaterial({
    vertexShader: screenVertex,
    fragmentShader: refractionFragment,
    depthTest: false,
    depthWrite: false,
    uniforms: {
      sceneColor: { value: this.target.texture },
      immersion: { value: 0 },
      phase: { value: 0 },
    },
  });
  private quad = new T.Mesh(new T.PlaneGeometry(2, 2), this.material);
  private active = false;
  constructor() {
    this.scene.add(this.quad);
  }
  resize(width: number, height: number) {
    this.target.setSize(
      Math.max(1, Math.round(width)),
      Math.max(1, Math.round(height)),
    );
  }
  render(
    renderer: T.WebGLRenderer,
    scene: T.Scene,
    camera: T.Camera,
    immersion: number,
    phase: number,
  ) {
    if (immersion <= 0) {
      if (this.active) this.target.dispose();
      this.active = false;
      renderer.setRenderTarget(null);
      renderer.render(scene, camera);
      return;
    }
    this.active = true;
    this.material.uniforms.immersion.value = immersion;
    this.material.uniforms.phase.value = phase;
    renderer.setRenderTarget(this.target);
    renderer.render(scene, camera);
    renderer.setRenderTarget(null);
    renderer.render(this.scene, this.camera);
  }
  dispose() {
    this.target.dispose();
    this.material.dispose();
    this.quad.geometry.dispose();
    this.scene.clear();
  }
}
