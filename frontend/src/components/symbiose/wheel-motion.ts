import { ACTIVE_WHEEL_SLOT, wheelSlots } from "../../symbiose-navigation";

const COUNT = wheelSlots.length;
const modulo = (value: number, period: number) =>
  ((value % period) + period) % period;
const clamp = (value: number) => Math.max(0, Math.min(1, value));
const smooth = (value: number) => {
  const t = clamp(value);
  return t * t * (3 - 2 * t);
};

// La progression n'est pas bornée : le passage 5 → 0 reste un seul cran.
// À équidistance, toujours préférer le sens croissant des rubriques.
export function nearestWheelTarget(position: number, index: number) {
  return index + COUNT * Math.floor((position - index) / COUNT + 0.5);
}

export function wheelPose(index: number, progression: number) {
  // Le raccord cyclique se fait à mi-chemin entre deux crans, à opacité nulle.
  const slot =
    modulo(index - progression + ACTIVE_WHEEL_SLOT + 0.5, COUNT) - 0.5;
  const segment = Math.max(0, Math.min(COUNT - 2, Math.floor(slot)));
  const t = slot - segment;
  const point = (i: number) => {
    if (i < 0)
      return {
        x: 2 * wheelSlots[0].x - wheelSlots[1].x,
        y: 2 * wheelSlots[0].y - wheelSlots[1].y,
      };
    if (i >= COUNT)
      return {
        x: 2 * wheelSlots[COUNT - 1].x - wheelSlots[COUNT - 2].x,
        y: 2 * wheelSlots[COUNT - 1].y - wheelSlots[COUNT - 2].y,
      };
    return wheelSlots[i];
  };
  const interpolate = (key: "x" | "y") => {
    const [a, b, c, d] = [-1, 0, 1, 2].map(
      (offset) => point(segment + offset)[key],
    );
    return (
      0.5 *
      (2 * b +
        (-a + c) * t +
        (2 * a - 5 * b + 4 * c - d) * t * t +
        (-a + 3 * b - 3 * c + d) * t * t * t)
    );
  };
  return {
    slot,
    x: interpolate("x"),
    y: interpolate("y"),
    opacity: smooth((slot + 0.5) / 0.5) * smooth((COUNT - 0.5 - slot) / 0.5),
    engagement: smooth(1 - Math.abs(slot - ACTIVE_WHEEL_SLOT) / 0.78),
  };
}

export function createWheelMotion(
  from: number,
  velocity: number,
  target: number,
) {
  const distance = Math.abs(target - from);
  const duration = 520 + Math.min(2, Math.max(0, distance - 1)) * 70;
  const driveDuration = duration * 0.82;
  // Dépassement plafonné à 2,2 % d'un cran, quelle que soit la distance.
  const detent =
    target +
    Math.sign(target - from || velocity) * Math.min(0.022, distance * 0.022);
  return { from, velocity, target, duration, driveDuration, detent };
}

export function sampleWheelMotion(
  motion: ReturnType<typeof createWheelMotion>,
  elapsed: number,
) {
  const { from, velocity, target, duration, driveDuration, detent } = motion;
  if (elapsed >= duration) return { position: target, velocity: 0, done: true };
  if (elapsed <= 0) return { position: from, velocity, done: false };
  if (elapsed < driveDuration) {
    const u = elapsed / driveDuration;
    const travel = 10 * u ** 3 - 15 * u ** 4 + 6 * u ** 5;
    const travelSpeed = 30 * u ** 2 - 60 * u ** 3 + 30 * u ** 4;
    // Hermite quintique : conserve la vitesse lors d'une interruption,
    // puis freine sans rupture avant le très court retour au cran.
    const inertia = u - 6 * u ** 3 + 8 * u ** 4 - 3 * u ** 5;
    const inertiaSpeed = 1 - 18 * u ** 2 + 32 * u ** 3 - 15 * u ** 4;
    return {
      position:
        from + (detent - from) * travel + velocity * driveDuration * inertia,
      velocity:
        ((detent - from) * travelSpeed) / driveDuration +
        velocity * inertiaSpeed,
      done: false,
    };
  }
  const settleDuration = duration - driveDuration;
  const u = (elapsed - driveDuration) / settleDuration;
  return {
    position: detent + (target - detent) * smooth(u),
    velocity: ((target - detent) * 6 * u * (1 - u)) / settleDuration,
    done: false,
  };
}
