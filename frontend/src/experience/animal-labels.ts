import type { AnimalBox } from "./world-fauna";
export function layoutAnimalLabels(animals: AnimalBox[]) {
  const occupied: { x: number; y: number }[] = [];
  return [...animals]
    .sort((a, b) => a.x - b.x)
    .map((animal) => {
      const x = Math.max(0.64, Math.min(0.81, animal.x));
      let y = Math.max(0.19, Math.min(0.73, animal.y - 0.041));
      for (
        let i = 0;
        i < 12 &&
        occupied.some(
          (p) => Math.abs(p.x - x) < 0.17 && Math.abs(p.y - y) < 0.035,
        );
        i++
      )
        y -= 0.041;
      y = Math.max(0.15, y);
      occupied.push({ x, y });
      return { ...animal, labelX: x, labelY: y };
    });
}
