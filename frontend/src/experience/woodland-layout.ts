import { riverWidth, riverX, seededRandom } from "./world-utils";
/** Curved field boundaries with clear space around the river. */
export function hedgerowPlacements(center: number) {
  const random = seededRandom(Math.abs(center) + 801);
  return Array.from({ length: 64 }, (_, i) => {
    const side = i < 32 ? -1 : 1;
    const z = Math.max(-640, center - 64 + (i % 32) * 4.2);
    let x = side * (52 + 13 * Math.sin(z * 0.027) + random() * 3);
    if (z < -165 && z > -525 && Math.abs(x - riverX(z)) < riverWidth(z) + 14)
      x += side * 24;
    return {
      x,
      z,
      height: 4 + random() * 3,
      angle: random() * Math.PI * 2,
      tint: 1,
    };
  });
}
export function woodlandPlacements(
  center: number,
  count: number,
  seed: number,
  forest: boolean,
) {
  const random = seededRandom(seed);
  return Array.from({ length: count }, (_, i) => {
    const candidate = center + (random() - 0.5) * (forest ? 165 : 80);
    const z =
      center < -800 ? Math.min(-875, candidate) : Math.max(-640, candidate);
    let x =
      (i % 2 ? -1 : 1) * (forest ? 14 + random() * 43 : 22 + random() * 135);
    if (z < -165 && z > -525 && Math.abs(x - riverX(z)) < riverWidth(z) + 14)
      x += x < 0 ? -35 : 35;
    if (Math.hypot(x - 14, z + 458) < 24) x += 30;
    return {
      x,
      z,
      height: forest ? 17 + random() * 9 : 10 + random() * 9,
      angle: random() * Math.PI * 2,
      tint: 0.9 + random() * 0.2,
    };
  });
}
