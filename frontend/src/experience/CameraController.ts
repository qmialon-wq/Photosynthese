import { PerspectiveCamera } from "three";
import { cameraKeys, narrativeDuration, type Vec3 } from "./config";
import { clamp01 } from "./journey";

export { clamp01, smoothstep } from "./journey";

/** Time-aware cubic Hermite interpolation: continuous position AND velocity at chapter seams. */
export function sampleCamera(progress: number) {
  const time = clamp01(progress) * narrativeDuration;
  let index = cameraKeys.findIndex((key) => key.time >= time);
  if (index <= 0) index = index === 0 ? 1 : cameraKeys.length - 1;
  const a = cameraKeys[index - 1],
    b = cameraKeys[index];
  const prev = cameraKeys[Math.max(0, index - 2)],
    next = cameraKeys[Math.min(cameraKeys.length - 1, index + 1)];
  const span = b.time - a.time;
  const t = clamp01((time - a.time) / span);
  const interpolate = (p: number, x: number, y: number, n: number) => {
    const m0 = ((y - p) / (b.time - prev.time)) * span;
    const m1 = ((n - x) / (next.time - a.time)) * span;
    return (
      (2 * t ** 3 - 3 * t ** 2 + 1) * x +
      (t ** 3 - 2 * t ** 2 + t) * m0 +
      (-2 * t ** 3 + 3 * t ** 2) * y +
      (t ** 3 - t ** 2) * m1
    );
  };
  const vector = (field: "position" | "target") =>
    [0, 1, 2].map((axis) =>
      interpolate(
        prev[field][axis],
        a[field][axis],
        b[field][axis],
        next[field][axis],
      ),
    ) as unknown as Vec3;
  return {
    position: vector("position"),
    target: vector("target"),
    fov: interpolate(prev.fov, a.fov, b.fov, next.fov),
  };
}

export class CameraController {
  readonly camera = new PerspectiveCamera(57, 1, 0.1, 1200);
  update(progress: number) {
    const pose = sampleCamera(progress);
    this.camera.position.set(...pose.position);
    this.camera.lookAt(...pose.target);
    this.camera.updateMatrixWorld(true);
    if (this.camera.fov !== pose.fov) {
      this.camera.fov = pose.fov;
      this.camera.updateProjectionMatrix();
    }
    return pose;
  }
  resize(width: number, height: number) {
    this.camera.aspect = width / Math.max(1, height);
    this.camera.updateProjectionMatrix();
  }
}
