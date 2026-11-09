# Audit graphique Symbiose — étape 7

Audit réalisé le 9 novembre 2026 sur les six routes de démonstration existantes. Le backend, les données et les traitements métier restent hors du périmètre.

## Références et limites

Les fichiers `Symbiose_Accueil.png`, `Symbiose_Connexion.png` et les cinq autres maquettes ne sont présents ni dans le dépôt ni dans les pièces jointes accessibles à cette session. La vérification porte donc sur la cohérence des composants, les captures de l’application avant et après correction et les descriptions fournies. La fidélité pixel par pixel aux maquettes reste **non vérifiée**.

La page Connexion existe à `/connexion`. Son affichage et ses interactions frontend sont testés avec une API d’authentification interceptée. La disponibilité réelle du serveur d’authentification et les comptes ne sont pas validés par cet audit graphique.

## Phase A — constats

- Un seul `AppShell` contient déjà les six routes ; il n’est pas dupliqué dans les pages.
- L’ordre cyclique et les six emplacements de la roue sont corrects. Les tests unitaires existants couvrent les six permutations.
- La pilule active possédait plusieurs règles concurrentes : largeur automatique, limites et exceptions par route. Sur mobile, sa hauteur dépendait du libellé.
- Lorsqu’une transition était interrompue, seule sa première image reprenait la position courante ; les suivantes repartaient de l’ancien emplacement, avec un risque de saut. Un effet de disparition réduisait aussi l’opacité lors des longs déplacements.
- Le fond, les paramètres et l’en-tête dépendaient de la hauteur du contenu. Le cadrage du fond et la position des paramètres pouvaient varier entre pages longues.
- Les styles des composants communs étaient mêlés aux styles de la Vidéothèque. Des gradients, couleurs de sélection et badges étaient répétés.
- Le focus explicite ne couvrait pas les listes déroulantes. Le bouton « Effacer la sélection » débordait légèrement sur mobile.

## Phase B — corrections globales

- `WheelNavigation` conserve six liens stables et leurs pictogrammes. La rubrique active reste au quatrième emplacement. La pilule desktop reste à **186 × 62 px**, avec le fond translucide et l’arc existants. Les libellés longs passent sur deux lignes ; la pilule mobile garde une hauteur fixe.
- Une transition interrompue repart désormais de sa position interpolée sur la trajectoire. Les icônes restent droites et opaques. Les animations sont annulées lorsqu’on active la réduction des mouvements, dans les paramètres ou via la préférence système.
- L’en-tête, la roue, le fond et les paramètres sont attachés au viewport. Leur géométrie est indépendante du contenu et du défilement.
- `symbiose.css` centralise les couleurs d’action, de statut, de sélection, de focus, de contrôle et les niveaux de verre.
- `GlassPanel` expose les profondeurs `panel`, `page`, `card`, `inset`. Les cartes vidéo, dossiers et observations partagent le niveau `card`.
- `symbiose-controls.css`, chargé une seule fois, rassemble les boutons secondaires, cases à cocher, champs, listes, pagination, états vides et fenêtres modales. Les chevrons restent centrés malgré les variations de hauteur des champs.
- Le badge de l’Accueil réutilise `StatusBadge`, avec une variante explicite de placement. La couleur des actions destructives utilise une variante commune.

## Phase C — vérification par page

| Page | Éléments examinés | Correction spécifique |
| --- | --- | --- |
| Accueil | 4 statistiques, 3 étapes, diagnostic, recommandation, 3 dernières analyses | Badge partagé ; cadre stable sur les pages longues |
| Vidéothèque | Statistiques, actions, filtres, cartes, sélection, badges, pagination | Verre des cartes commun et styles des contrôles extraits |
| Mes dossiers | Recherche, filtres, 6 dossiers, photos, statuts, menus, pagination | Verre des cartes commun ; chevrons centrés |
| Analyses | Lecteur, détection, réglages, actions et messages | Panneau principal harmonisé, cadre et focus communs |
| Validation humaine | Filtres, sélection multiple, 8 observations, validation, durées | Verre des cartes commun ; bouton mobile pouvant passer sur deux lignes |
| Documents scientifiques | En-tête, corpus, espèce, actions, états vides, avancement | Variante destructive commune ; chevron centré |

Les différences de disposition liées au contenu sont conservées. Aucune fonctionnalité métier supplémentaire n’a été ajoutée.

## Phases D et E — vérification et livrables

Les captures initiales des six rubriques sont conservées dans `output/symbiose/etape-7/avant/`. Les captures finales sont dans `output/symbiose/etape-7/final/` : six pages à 1920 × 1080, 1600 × 900, 1440 × 900, 1280 × 800 et 390 × 844, ainsi que Connexion en desktop et mobile. Les captures finales représentent le viewport ; les pages longues restent accessibles par défilement vertical.

Ouvrir `output/symbiose/etape-7/index.html` pour comparer les six vues avant/après avec un curseur, puis accéder à la galerie des résolutions et aux résultats mesurés.

Pour reproduire depuis `frontend/` :

```powershell
npm run dev -- --port 4173
# Dans un autre terminal :
node scripts/audit-capture.mjs final
npm test
npm run build
npx playwright test tests/e2e/harmonisation-design.spec.ts
npx playwright test tests/e2e/symbiose-design.spec.ts tests/e2e/videotheque-design.spec.ts tests/e2e/dossiers-design.spec.ts tests/e2e/analyse-design.spec.ts tests/e2e/validation-design.spec.ts tests/e2e/documents-design.spec.ts tests/e2e/login-design.spec.ts tests/e2e/profile-logout.spec.ts
```

Les tests de démonstration n’exigent pas le backend. Les tests historiques des écrans métier ne sont pas couverts par cet audit.

## Résultats définitifs

| Vérification | Résultat |
| --- | --- |
| `npm test` | **46 tests unitaires réussis**, 12 fichiers |
| `npm run build` | **Réussi**, contrôle TypeScript et compilation Vite |
| Suite Playwright de 46 scénarios | **45 réussis** au premier passage complet ; une assertion obsolète dans le test de connexion attendait le titre de l’ancien Accueil |
| Recontrôle du scénario de connexion corrigé | **1/1 réussi** : erreur d’identifiants, nouvelle tentative, arrivée sur Accueil et profil « Camille » |
| Total des scénarios navigateur validés | **46/46**, après correction de cette assertion ; aucun changement applicatif requis pour la connexion |
| Navigation animée | **36/36 combinaisons** vérifiées à 1600 × 900, sans erreur de page |
| Géométrie du cadre et de la roue | Identique sur les six rubriques, pour chacune des cinq résolutions, y compris après défilement |
| Mesures des 30 vues des rubriques | **0 débordement horizontal, 0 libellé contrôlé coupé, 0 erreur navigateur** |
| Galerie comparative | 6 curseurs fonctionnels, 12 images chargées |
| `git diff --check` | Réussi |

Les scénarios Playwright couvrent les recherches, filtres, paginations, sélections, menus, modales, états vides, simulations d’analyse et de validation, lecture locale, raccourcis et focus clavier, mouvements réduits, historique de navigation et déconnexion. Les analyses automatisées d’accessibilité Axe des états testés passent. Elles ne constituent pas une certification exhaustive d’accessibilité.

Les résultats bruts sont conservés dans `tests-interactions.json`, le recontrôle dans `tests-connexion.json`, les 36 combinaisons dans `transitions.json` et les mesures dans `final/verification.json`, sous `output/symbiose/etape-7/`.

### Corrigé

Roue stable, dimensions et libellés, reprise d’animation, réduction des mouvements en cours de transition, cadre indépendant de la hauteur des pages, niveaux de verre et contrôles partagés, focus des listes, alignement des chevrons, bouton mobile de validation et assertion de connexion périmée.

### Validé

Six rubriques, Connexion existante, comportements frontend mentionnés ci-dessus, cinq résolutions demandées, captures finales, composants communs, compilation et tests.

### Non vérifié / restant

- Comparaison aux maquettes originales absentes : reste à réaliser lorsqu’elles seront disponibles.
- Tests sur Firefox, Safari et appareils mobiles réels : navigateur utilisé ici, Chromium de Playwright.
- Backend, traitements métier et authentification contre un serveur réel : hors périmètre. Les simulations restent explicitement présentées comme telles.
