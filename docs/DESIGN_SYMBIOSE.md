# Socle graphique Symbiose

La vue de validation utilise la stack existante : Vue 3, TypeScript et Vue Router. Elle est accessible sans connexion et ne charge aucune donnée métier depuis l’API. Le fond forestier couvre tout l’écran, sans cadre extérieur.

Le menu du profil propose « Se déconnecter ». Cette action réutilise l’authentification existante : récupération de la session et du jeton CSRF si nécessaire, fermeture de session, puis retour à `/connexion`. Une session déjà expirée permet également ce retour ; une erreur du serveur reste affichée dans le menu et permet de réessayer.

Depuis `frontend/`, lancer `npm ci` si nécessaire, puis `npm run dev`. Ouvrir l’URL affichée par Vite. La compilation se fait avec `npm run build`.

Les routes `/`, `/videos`, `/parcelles`, `/analyses`, `/review` et `/documents` présentent le socle graphique. L’Accueil, la Vidéothèque et Mes dossiers sont intégrés ; les trois autres rubriques restent des pages provisoires. Les anciens écrans métier restent dans le dépôt, et les routes d’administration existantes conservent leur fonctionnement. Les valeurs de `src/data/home-preview.ts`, `src/data/video-preview.ts` et `src/data/project-preview.ts` sont explicitement fictives. Aucun backend ou stockage supplémentaire n’a été ajouté.

## Composants et variables

- `src/components/symbiose/AppShell.vue` : cadre forestier, marque, trois actions de l’en-tête et paramètres indépendants.
- `WheelNavigation.vue` : six liens stables, état actif dérivé de l’URL, déplacement le long de l’arc par l’API d’animation du navigateur, pictogrammes fixes, navigation au clavier et mouvements réduits.
- `GlassPanel.vue`, `StatCard.vue`, `PillButton.vue`, `SymIcon.vue`, `TopographicPattern.vue` : composants visuels réutilisables.
- `src/styles/symbiose.css` : variables `--sym-*` pour couleurs, police, verre, bordure, ombre, rayon, espacements et animation. Les styles sont isolés des anciens écrans.
- `src/symbiose-navigation.ts` : ordre cyclique unique et coordonnées des six emplacements. Le quatrième emplacement est toujours actif. Un changement d’URL repositionne les six liens ; l’arc reste fixe. La pilule active garde un fond vert translucide, une bordure lumineuse et un texte blanc.

Pour intégrer une future page, conserver sa route et ses métadonnées `designPreview`, remplacer uniquement son composant provisoire et utiliser les composants communs. L’AppShell n’a pas à être reconstruit.

À chaque nouvelle étape, réaliser deux captures finales en 1600 × 900 : la page intégrée et l’Accueil. Les conserver dans `output/symbiose/etape-N/`, hors du dossier temporaire des tests. Comparer aussi l’Accueil après un aller-retour vers la nouvelle page pour détecter les styles qui débordent sur les composants communs. La roue doit conserver ses six positions, son arc et sa pilule active.

## Vérification

- `npm test` : tests unitaires, dont les six permutations cycliques de la roue.
- `npx playwright test tests/e2e/symbiose-design.spec.ts` : Accueil en 1600 × 900, accessibilité, absence d’appels API, six rotations, positions fixes, historique du navigateur, clavier, actions et adaptation mobile. Les captures sont dans `frontend/test-results/`.
- `npx playwright test tests/e2e/profile-logout.spec.ts` : déconnexion après rechargement, session absente, erreur serveur et nouvelle tentative.
- `npx playwright test tests/e2e/videotheque-design.spec.ts` : captures jumelées, Accueil identique avant/après visite, ordre de la roue, pilule active de même taille, sélection entre pages, filtres, pagination, menus, simulations et mobile. Voir `VIDEOTHEQUE_SYMBIOSE.md`.
- `npx playwright test tests/e2e/dossiers-design.spec.ts` : captures des trois pages, non-régression visuelle, ordre et styles de la roue, filtres et pagination des dossiers, aperçu fictif, menus au clavier et mobile. Voir `DOSSIERS_SYMBIOSE.md`.

Les tests fonctionnels historiques des écrans métier ne décrivent pas le nouveau mode de validation graphique : ses six routes sont volontairement provisoires.

## Ressources graphiques

Le logo existant `frontend/src/assets/symbiose-logo.png` est conservé. Les photographies suivantes ont été préparées avec l’outil intégré `image_gen` ; aucun service de génération n’est appelé par l’application.

### Fond de l’Accueil

Fichier final : `frontend/src/assets/home-forest.png`. Référence : la maquette Symbiose_Accueil fournie par l’utilisateur. Le fond de connexion existant reste indépendant.

Consigne exacte :

> Use case: precise-object-edit. Edit target: supplied Symbiose dashboard reference image. Extract/reconstruct ONLY its immersive forest background. Remove ALL UI: every glass panel, card, gauge, chart, text, logo, number, badge, button, navigation icon, circular arc, gear, all topographic graphic lines, thumbnail photographs, black outer margin and white outer border. Fill the removed areas seamlessly with a natural forest matching the original background, with golden soft sunlight and leaves upper left, deep rich blurred green forest trunks center and right, vivid moss covered foreground rock bottom left and green foliage along the bottom. Preserve the photographic lighting, colors and visual mood of the original forest faithfully. Soft shallow depth of field in the middle distance. This is a full bleed landscape 16:9 website BACKGROUND photograph, no interface, no text, no logo, no lines, no frame, no deer or other animals. Dark calm green negative space on the right for real HTML panels to be overlaid.

### Vignettes photographiques

Fichier final : `frontend/src/assets/biodiversity-thumbnails.png`. Quatre photographies dans une seule planche, affichées par position d’arrière-plan CSS. Les panneaux, données, textes, icônes et contrôles sont de vrais éléments Vue/HTML/SVG, pas une capture de maquette.

Consigne exacte :

> Create a photographic contact sheet of exactly four equally-sized rectangular photographs arranged in a seamless 2 by 2 grid, no margins or borders, total landscape aspect ratio 3:2. This is a production asset containing ONLY photographs for tiny biodiversity dashboard thumbnails. Top left: lush Norman countryside hedgerows, green rolling meadow and mature trees, warm natural daylight. Top right: a full body roe deer standing in a green European forest clearing, natural camera trap perspective. Bottom left: a full body red fox standing in green grass in a European forest, side profile looking towards camera. Bottom right: a full body European badger walking through moss and fallen leaves in a European woodland, side profile. Each photograph must be independently composed and photorealistic with rich natural greens, clearly visible subject, soft sunny light. No text, no typography, no icons, no logos, no controls, no UI, no map or graphics.

