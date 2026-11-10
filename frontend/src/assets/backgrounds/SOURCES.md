# Fonds photographiques Symbiose

Sources vérifiées et téléchargées le 10 novembre 2026. Toutes les images sont servies localement ; aucun appel à Unsplash n’est effectué par l’application.

| Fichier | Photographe et page source | Sujet | Identifiant de l’image originale sur images.unsplash.com |
| --- | --- | --- | --- |
| `forest.webp` | Fond Symbiose préexistant : `../home-forest.png` | Forêt originale | Sans nouvelle source externe ; provenance historique inchangée |
| `sky.webp` | [Artem](https://unsplash.com/photos/8_uRtr9QUS0) | Nuages légers dans un ciel bleu | `photo-1761166478784-dc565cffb472` |
| `river.webp` | [Billy Freeman](https://unsplash.com/photos/TyOuzLDcqiE) | Rivière dans une forêt automnale | `photo-1628439775403-4e28009aed38` |
| `underwater.webp` | [Erick Morales Oyola](https://unsplash.com/photos/vHDLjO-iW8k) | Laminaires et rayons de soleil, Anacapa Island, Californie | `photo-1745917784526-fbad88531db1` |
| `wetland.webp` | [Pascal Debrunner](https://unsplash.com/photos/2lPR-5MUliw) | Zone humide, roseaux et brume au lever du soleil, Suisse | `photo-1773311400657-29c0891cc045` |
| `meadow.webp` | [Tanya Barrow](https://unsplash.com/photos/c7Igx8X-XRI) | Prés vallonnés et haies dans la brume ; localisation non précisée par la source | `photo-1758796626075-191ac8ce321e` |
| `coast.webp` | [Sergei Gussev](https://unsplash.com/photos/aoY9DHy334Y) | Falaises d’Étretat depuis La Poterie-Cap-d’Antifer, Normandie | `photo-1749195403680-e6c8fe1d98b2` |
| `night-forest.webp` | [Mike Dierken](https://unsplash.com/photos/t1QCaQ9vu6E) | Sentier forestier au clair de lune, mont Rainier | `photo-1755386228574-d431a8699f91` |

## Licence et crédits

Les sept pages Unsplash indiquaient « Free to use under the Unsplash License » au moment de la vérification. Ce sont des photos gratuites, sans abonnement Unsplash+.

La [licence Unsplash](https://unsplash.com/license) autorise le téléchargement, la modification et l’utilisation, y compris commerciale. L’attribution est appréciée mais facultative ; les crédits sont néanmoins conservés ici et affichés dans les paramètres pour le fond sélectionné. La licence interdit la vente des images sans modification significative et leur compilation pour créer un service similaire ou concurrent. Conserver ce fichier avec les assets. Aucun transfert de propriété ni nouvelle licence n’est revendiqué pour le fond forestier préexistant.

## Préparation des fichiers

- Forêt : conversion WebP **sans perte**, 1672 × 941, même composition et mêmes pixels RGB que `home-forest.png`.
- Autres photos : téléchargement depuis `https://images.unsplash.com/<identifiant>?auto=format&fit=crop&w=2560&h=1440&q=88&fm=jpg`, puis WebP qualité 85, méthode 6 avec Pillow. Recadrage central en 16:9, sans ajout ni génération d’image.
- Chaque fichier `*-thumb.webp` est une miniature distincte de 320 × 180, qualité 76 (80 pour la forêt).
- Poids total des huit fonds : environ 4,8 Mio. Le fond choisi est chargé en priorité ; les sept autres grandes images ne sont pas préchargées.
- Les miniatures de galerie montrent la photo sans voile ; les voiles de contraste sont définis séparément dans `src/config/background-themes.ts`.

Aucune image ne reste à fournir.
