import type { WebGLRenderer } from "three";
export class AtmosphereController {
  update(renderer: WebGLRenderer, night: number) {
    renderer.toneMappingExposure = 1.12 - night * 0.08;
  }
}
