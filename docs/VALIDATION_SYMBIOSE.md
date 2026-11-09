# Validation humaine — étape 5

La page graphique `/review` reproduit la structure de la maquette avec une grille de quatre colonnes et deux lignes à 1600 × 900. Documents scientifiques reste une page provisoire. La stack Vue 3, TypeScript et Vue Router est conservée.

## Composants réutilisés et nouveaux fichiers

AppShell, WheelNavigation, GlassPanel, FilterSelect, DemoDialog, StatusBadge, VideoPlayer et les boutons existants sont réutilisés.

- `frontend/src/pages/DesignValidationPage.vue` : filtres, sélection visible et dialogues de confirmation.
- `frontend/src/components/symbiose/ObservationCard.vue` : case à cocher, vignette, durée, espèce, fichier, état et contexte.
- `BulkSelectionToolbar.vue` : sélection de la page, compteur, espèce à attribuer et actions groupées.
- `ValidationPreviewModal.vue` : aperçu via le lecteur de l’étape 4 ; le lecteur est démonté à la fermeture pour interrompre la lecture.
- `frontend/src/data/observation-preview.ts` : données fictives, filtres et opérations locales, sans mutation des données initiales.
- `frontend/src/styles/validation.css` : styles propres à la nouvelle page, préfixés `sr-`.

Le code de WheelNavigation, son arc, ses positions et ses animations restent identiques. Deux règles CSS limitées au bouton actif `/review` sur desktop permettent de conserver les dimensions du bouton Accueil (186 × 62 px). Le libellé blanc se répartit sur deux lignes ; le fond translucide, la bordure, les ombres et la position restent identiques. Les quatre autres pages gardent leurs styles.

## Données et interactions

Huit observations locales sont affichées : sept aperçus de chevreuil et une vidéo locale d’écureuil. Les aperçus de chevreuil réutilisent `analysis-deer.png` avec des positions d’arrière-plan CSS. Aucun nouveau recadrage ou visuel n’est extrait ou généré. Le clip d’écureuil réutilise `squirrel-local.mp4` ; sa vignette affiche une image lue par le navigateur à environ 1,5 seconde. Aucune vidéo de chevreuil correspondant aux noms fictifs n’existe : la modale indique explicitement que sa lecture est simulée.

Toutes les espèces proposées, qualités, statuts et fenêtres « 15 s avant / 20 s après » sont des données de démonstration. La fenêtre de contexte ne décrit pas la durée ou les capacités d’extraction du clip local.

Deux observations, 6 et 7, représentent des images de test protégées. Elles peuvent être consultées, mais ne peuvent être sélectionnées, validées ou retirées. La sélection globale porte donc sur six observations éditables dans la vue initiale. Les opérations locales vérifient également cette protection indépendamment des cases à cocher.

Les filtres d’espèce et de qualité s’appliquent ensemble. Toute modification de filtre efface la sélection, qui reste limitée au contenu actuellement affiché. Les cartes sélectionnées reçoivent une bordure lumineuse ; la case globale affiche un état intermédiaire pour une sélection partielle.

Valider la sélection nécessite une observation et une espèce. La confirmation explicite attribue l’espèce et le statut Validée dans l’état frontend. Le nom de fichier et l’espèce suggérée initiale restent conservés dans les données. Annuler laisse les observations et la sélection intactes.

Effacer la sélection ouvre une seconde confirmation et retire uniquement les cartes éditables choisies de la liste en mémoire. Aucun fichier réel n’est supprimé. Les deux opérations effacent la sélection après confirmation et affichent un retour de démonstration.

Un rechargement ou un retour vers cette page recrée les huit observations initiales. Aucune donnée métier, API, IA, base de données, localStorage ou sessionStorage n’est utilisée pour ces actions.

## Lancement et vérification

Depuis `frontend/` :

```powershell
npm run dev -- --port 4173
npm run build
npm test
npx playwright test tests/e2e/validation-design.spec.ts tests/e2e/analyse-design.spec.ts tests/e2e/symbiose-design.spec.ts tests/e2e/videotheque-design.spec.ts tests/e2e/dossiers-design.spec.ts tests/e2e/profile-logout.spec.ts
```

Les tests couvrent la grille et son adaptation à 1280, 1000 et 390 px, l’accessibilité, les huit cartes, la sélection partielle/globale, les protections, les filtres combinés et l’état vide, l’annulation et la confirmation des opérations, l’absence de stockage permanent, les deux modes du lecteur et son arrêt à la fermeture. Les tests de navigation comparent aussi l’Accueil, la Vidéothèque, Mes dossiers et Analyse vidéo avant et après un passage par Validation humaine : captures hors éléments animés, puis géométrie, styles et pictogrammes de la roue séparément.

Validation effectuée : 41 tests unitaires et 29 tests navigateur réussis (7 pour cette page et 22 pour le socle et les étapes précédentes). Compilation TypeScript/Vite réussie. Les tests de la nouvelle page ne relèvent aucun appel API ni erreur JavaScript.

Le seul service Docker frontend a été reconstruit. Le contrôle final à 1600 × 900 retrouve une géométrie et une typographie identiques sur les 831 éléments mesurés des quatre pages précédentes. Les cinq pages répondent sans erreur JavaScript ni appel API ; le contrôle mobile à 390 px ne relève aucun débordement horizontal. Le détail est conservé dans `output/symbiose/etape-5/verification.json`.

Les captures finales sans masquage à 1600 × 900 sont conservées dans `output/symbiose/etape-5/` :

- `validation-humaine-1600x900.png`
- `accueil-1600x900.png`
- `videotheque-1600x900.png`
- `mes-dossiers-1600x900.png`
- `analyse-video-1600x900.png`
