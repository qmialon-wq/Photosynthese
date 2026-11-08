# Symbiose — Étape 2 : Vidéothèque

La route `/videos` utilise `DesignVideosPage.vue` dans l’AppShell existant. L’Accueil, la Connexion et les quatre pages provisoires ne sont pas modifiés. Aucun backend ou appel API n’a été ajouté à la Vidéothèque.

## Réutilisation

Le fond, `AppShell`, `WheelNavigation`, `GlassPanel`, `StatCard`, `SymIcon` et les variables CSS `--sym-*` sont conservés. Les styles de la nouvelle page sont isolés dans `frontend/src/styles/videotheque.css`, chargés avec la page, avec des classes `sv-*`.

Les composants réutilisables ajoutés dans `frontend/src/components/symbiose/` sont `VideoCard`, `SearchField`, `FilterSelect`, `StatusBadge`, `Pagination` et `DemoDialog`.

La seule correction de présentation commune concerne les libellés de navigation de longueur intermédiaire : ils tiennent désormais dans une pilule de 186 × 62 px, comme l’Accueil à 1600 × 900. L’arc, les six coordonnées, l’ordre et l’animation de la roue restent inchangés. Les chemins SVG des nouvelles icônes sont ajoutés à la bibliothèque existante. La capture de l’Accueil avant intégration a été conservée pour la comparaison visuelle.

## Démonstration locale

`frontend/src/data/video-preview.ts` contient 248 entrées explicitement fictives, les indicateurs et les options des filtres. La pagination présente quatre résultats par page, soit 62 pages sans filtre. La recherche porte sur le nom du fichier, la parcelle et l’espèce, sans distinction de casse ou d’accents.

La sélection est conservée entre les pages et les filtres. La case globale sélectionne uniquement les résultats de la page visible et indique une sélection partielle. Les actions d’import, de préparation et de lecture ouvrent des fenêtres clairement identifiées comme démonstrations. Aucun fichier n’est transféré et aucun dossier métier n’est créé.

## Vérification et captures

Depuis `frontend/` :

- `npm run dev` : lancer le frontend.
- `npm run build` et `npm test` : compiler et vérifier les tests unitaires.
- `npx playwright test tests/e2e/videotheque-design.spec.ts tests/e2e/symbiose-design.spec.ts tests/e2e/profile-logout.spec.ts` : vérifier la nouvelle page et le socle commun.

Le test de captures jumelées produit `accueil-1600x900.png`, `videotheque-1600x900.png` et `accueil-apres-videotheque-1600x900.png` dans son répertoire `frontend/test-results/`. Les captures livrées sont complètes. La comparaison automatisée de l’Accueil avant/après visite masque la pilule active et la petite note translucide de démonstration, dont le rendu peut être recomposé par Chromium après l’animation ; la géométrie, la couleur, la bordure et l’ombre de la pilule sont vérifiées séparément. Le reste de l’écran est comparé à l’octet près. Le test contrôle également le même SVG d’arc et l’absence d’appels à l’API.

Les captures finales prises sur la version locale Docker sont conservées sous `output/symbiose/etape-2/accueil-1600x900.png` et `output/symbiose/etape-2/videotheque-1600x900.png`. Ce dossier persiste après le nettoyage des résultats de tests et sert de référence pour les prochaines étapes.

## Photographies

Les photographies du chevreuil, du renard et du blaireau réutilisent `frontend/src/assets/biodiversity-thumbnails.png`. Le fond commun reste `home-forest.png`.

La photographie complémentaire du sanglier est enregistrée dans `frontend/src/assets/video-boar.png`. Elle a été créée avec l’outil intégré `image_gen`, sans service de génération dans l’application.

Consigne exacte :

> Photorealistic landscape 3:2 wildlife photograph for a biodiversity video thumbnail. A full body European wild boar, side profile facing right, walking on moss and green undergrowth in a lush temperate European forest. Animal centered and fully visible with natural brown fur, sunlit green leaves and soft tree trunks behind it. Natural camera trap viewpoint near ground level, soft warm daylight, rich forest green palette matching a premium forest biodiversity dashboard. Clear recognizable animal, realistic proportions. Only the photograph, no interface, no text, no badge, no play icon, no frame, no watermark.

