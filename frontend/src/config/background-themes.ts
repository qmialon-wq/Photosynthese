export const backgroundIds = [
  "forest",
  "sky",
  "river",
  "underwater",
  "wetland",
  "meadow",
  "coast",
  "night-forest",
] as const;
export type BackgroundId = (typeof backgroundIds)[number];
export interface BackgroundTheme {
  id: BackgroundId;
  name: string;
  description: string;
  image: string;
  thumbnail: string;
  position: string;
  overlay: string;
  credit: string;
  source?: string;
}
// Vite resolves URLs at build time; importing a URL does not fetch the photograph.
const photos = import.meta.glob<string>("../assets/backgrounds/*.webp", {
  eager: true,
  query: "?url",
  import: "default",
});
function theme(
  id: BackgroundId,
  name: string,
  description: string,
  overlay: string,
  credit: string,
  source?: string,
  position = "center",
): BackgroundTheme {
  return {
    id,
    name,
    description,
    overlay,
    credit,
    source,
    position,
    image: photos[`../assets/backgrounds/${id}.webp`],
    thumbnail: photos[`../assets/backgrounds/${id}-thumb.webp`],
  };
}
export const backgroundThemes: readonly BackgroundTheme[] = [
  theme(
    "forest",
    "Forêt",
    "La forêt lumineuse originale de Symbiose.",
    "transparent",
    "Fond Symbiose original",
  ),
  theme(
    "sky",
    "Ciel et nuages",
    "Des nuages légers dans un ciel bleu pastel.",
    "linear-gradient(110deg, rgb(18 43 76 / 60%), rgb(10 30 56 / 68%))",
    "Artem",
    "https://unsplash.com/photos/8_uRtr9QUS0",
  ),
  theme(
    "river",
    "Rivière",
    "Une rivière traverse la forêt aux couleurs d’automne.",
    "linear-gradient(110deg, rgb(16 56 71 / 34%), rgb(8 37 51 / 48%))",
    "Billy Freeman",
    "https://unsplash.com/photos/TyOuzLDcqiE",
  ),
  theme(
    "underwater",
    "Monde sous-marin",
    "La lumière traverse une forêt de laminaires.",
    "linear-gradient(110deg, rgb(8 43 70 / 35%), rgb(4 28 52 / 55%))",
    "Erick Morales Oyola",
    "https://unsplash.com/photos/vHDLjO-iW8k",
  ),
  theme(
    "wetland",
    "Zones humides",
    "Roseaux et arbres se reflètent dans la brume du matin.",
    "linear-gradient(110deg, rgb(21 56 47 / 46%), rgb(10 35 29 / 56%))",
    "Pascal Debrunner",
    "https://unsplash.com/photos/2lPR-5MUliw",
  ),
  theme(
    "meadow",
    "Prairie et bocage",
    "Des prés et des haies ondulent sous la brume.",
    "linear-gradient(110deg, rgb(53 65 42 / 48%), rgb(28 37 21 / 58%))",
    "Tanya Barrow",
    "https://unsplash.com/photos/c7Igx8X-XRI",
  ),
  theme(
    "coast",
    "Littoral",
    "Les falaises d’Étretat au-dessus de la mer.",
    "linear-gradient(110deg, rgb(32 61 80 / 48%), rgb(13 35 51 / 62%))",
    "Sergei Gussev",
    "https://unsplash.com/photos/aoY9DHy334Y",
  ),
  theme(
    "night-forest",
    "Forêt nocturne",
    "Un sentier de conifères éclairé par la lune, au mont Rainier.",
    "linear-gradient(110deg, rgb(17 25 47 / 8%), rgb(8 13 30 / 15%))",
    "Mike Dierken",
    "https://unsplash.com/photos/t1QCaQ9vu6E",
  ),
];
export const defaultBackground = backgroundThemes[0];
export function findBackground(id: unknown): BackgroundTheme | undefined {
  return backgroundThemes.find((item) => item.id === id);
}
