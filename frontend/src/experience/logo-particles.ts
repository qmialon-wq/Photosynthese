/** Deterministic, evenly distributed coverage of the actual logo alpha, without duplicate random samples. */
export function logoParticleTargets(
  pixels: Uint8ClampedArray,
  width: number,
  height: number,
  budget = 7200,
): Float32Array {
  const candidates: number[] = [];
  for (let y = 0; y < height; y++)
    for (let x = 0; x < width; x++)
      if (pixels[(y * width + x) * 4 + 3] > 160) candidates.push(x, y);
  const count = Math.min(budget, candidates.length / 2),
    result = new Float32Array(count * 2);
  for (let i = 0; i < count; i++) {
    const index = Math.floor(((i + 0.5) * candidates.length) / 2 / count) * 2;
    result[i * 2] = candidates[index] / width - 0.5;
    result[i * 2 + 1] = 0.5 - candidates[index + 1] / height;
  }
  return result;
}
