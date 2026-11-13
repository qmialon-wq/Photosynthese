export interface PerformanceSample {
  fps: number;
  frameMs: number;
  quality: "standard" | "eco";
}

/** Measures frame delivery while moving. Idle, hidden-tab and startup frames are excluded. */
export class PerformanceMonitor {
  private start = 0;
  private frames = 0;
  private slowWindows = 0;
  private lastFrame = 0;
  private quality: "standard" | "eco" = "standard";
  constructor(
    private report: (sample: PerformanceSample) => void,
    private downgrade: () => void,
    quality: "standard" | "eco" = "standard",
  ) {
    this.quality = quality;
  }
  frame(now: number, moving: boolean) {
    if (!moving || document.hidden || now - this.lastFrame > 150) {
      this.start = 0;
      this.frames = 0;
      this.slowWindows = 0;
    }
    this.lastFrame = now;
    if (!moving || document.hidden) return;
    if (!this.start) this.start = now;
    this.frames++;
    const elapsed = now - this.start;
    if (elapsed < 1500) return;
    const fps = ((this.frames - 1) * 1000) / elapsed;
    this.slowWindows = fps < 36 ? this.slowWindows + 1 : 0;
    if (this.slowWindows >= 2 && this.quality === "standard") {
      this.quality = "eco";
      this.downgrade();
    }
    this.report({
      fps: Math.round(fps),
      frameMs: Math.round(1000 / fps),
      quality: this.quality,
    });
    this.frames = 1;
    this.start = now;
  }
}
