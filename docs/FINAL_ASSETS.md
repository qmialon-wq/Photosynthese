# Symbiose — inventaire des assets

Inventaire du 13 novembre 2026. Les masters fournis restent intacts.
17 dérivés : **32837763 → 4222222 octets**, soit **87.14 % de réduction**.
Ce total compare les mêmes images ; il ne mesure ni la mémoire GPU ni tout le dépôt.

| Milieu | Type | Dimensions | Source (octets) | Livraison (octets) |
|---|---|---|---:|---:|
| forest | [foreground](../frontend/public/experience-art/forest/foreground-runtime.webp) | 1280 × 720 | 1133993 | 176958 |
| forest | [primary](../frontend/public/experience-art/forest/primary-runtime.webp) | 1672 × 941 | 3186093 | 445902 |
| sky | [foreground](../frontend/public/experience-art/sky/foreground-runtime.webp) | 1280 × 720 | 1348666 | 223004 |
| sky | [primary](../frontend/public/experience-art/sky/primary-runtime.webp) | 1672 × 941 | 2478758 | 271386 |
| rivers | [foreground](../frontend/public/experience-art/rivers/foreground-runtime.webp) | 1280 × 720 | 1078840 | 218668 |
| rivers | [primary](../frontend/public/experience-art/rivers/primary-runtime.webp) | 1672 × 941 | 3249236 | 469552 |
| underwater | [foreground](../frontend/public/experience-art/underwater/foreground-runtime.webp) | 1280 × 720 | 1345816 | 220118 |
| underwater | [primary](../frontend/public/experience-art/underwater/primary-runtime.webp) | 1672 × 941 | 2161047 | 171046 |
| wetland | [foreground](../frontend/public/experience-art/wetland/foreground-runtime.webp) | 1280 × 720 | 1190845 | 210098 |
| wetland | [primary](../frontend/public/experience-art/wetland/primary-runtime.webp) | 1672 × 941 | 2931298 | 359804 |
| meadow | [foreground](../frontend/public/experience-art/meadow/foreground-runtime.webp) | 1280 × 720 | 1035076 | 190994 |
| meadow | [primary](../frontend/public/experience-art/meadow/primary-runtime.webp) | 1672 × 941 | 2971977 | 401264 |
| coast | [foreground](../frontend/public/experience-art/coast/foreground-runtime.webp) | 1280 × 720 | 942203 | 122082 |
| coast | [primary](../frontend/public/experience-art/coast/primary-runtime.webp) | 1672 × 941 | 2606590 | 266048 |
| night-forest | [foreground](../frontend/public/experience-art/night-forest/foreground-runtime.webp) | 1280 × 720 | 742407 | 119068 |
| night-forest | [primary](../frontend/public/experience-art/night-forest/primary-runtime.webp) | 1672 × 941 | 2600703 | 279996 |
| demo | [poster](../frontend/public/experience-media/manifesto-review.webp) | 1440 × 676 | 1834215 | 76234 |

Les SHA-256, dimensions et réglages exacts sont dans [runtime-assets.json](../frontend/public/experience-art/runtime-assets.json).
Les tests vérifient ces empreintes et la copie incluse dans le bundle.

## Provenance et état

- Huit masters et huit premiers plans générés : provenance, licences et états d'approbation conservés dans le [manifest artistique](../frontend/public/experience-art/manifest.json). Les **41 ressources absentes** restent inventoriées. Les trois flags d'approbation restent faux.
- WebP Pillow **10.3.0**, qualité RGB 88 (poster 90), premiers plans réduits à 1280 px. Alpha identique à la résolution de livraison, RGB avec pertes. Aucun détail natif 4K revendiqué. Régénération avec les dépendances fixées dans "frontend/scripts/requirements-assets.txt".
- Logo blanc du produit exact, sans redessin ; bitmap du logo échantillonné en particules puis fermé. Ciel local et géométrie procédurale illustratifs.
- Poster : capture du manifeste ARQ, page 7, explicitement statique. Les extraits nécessaires aux sources du jury sont embarqués. Les anciennes photos du produit ne sont pas réétiquetées Normandie.
- Aucune police, texture ou vidéo distante indispensable. Les liens de bibliographie restent consultables, sans appel nécessaire au pitch.
- **Montage produit de 90 s et sous-titres absents.** Aucun film fictif ne les remplace. Codec, résolution, débit, cadrage et compression ne sont donc pas validés. À préparer avec l'équipe : lecture locale compatible Chromium, 1080p maximum si suffisant pour les détails de l'interface, débit ajusté visuellement et VTT français.

## Pack

Révision **3aeae4f97a928ea3** : 31 ressources, **5460554 octets** dans le cache du jury.
Le manifeste "frontend/dist/jury/offline-manifest.json" liste chaque URL, poids et empreinte.
Le pack portable copie cette liste et ajoute le service worker, son manifeste, le serveur Node et son README.
Le total du cache ne comprend pas ces fichiers auxiliaires. Les PNG masters et la galerie de revue sont exclus.

Nginx compresse les textes, JS, CSS, JSON, SVG et VTT en gzip. WebP conserve sa compression propre.
Le serveur portable sert directement les fichiers et les requêtes Range, sans dépendance npm au lancement.
