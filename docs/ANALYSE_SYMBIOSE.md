# Analyse vidéo — étape 4

La page graphique est accessible sur `/analyses`. Elle conserve Vue 3, TypeScript, Vue Router, AppShell et WheelNavigation. Seule cette rubrique est intégrée à cette étape. La roue et les styles des trois pages précédentes restent identiques.

## Composants et données

- `frontend/src/pages/DesignAnalysisPage.vue` : disposition, sélection et cycle de démonstration.
- `frontend/src/components/symbiose/VideoPlayer.vue` : aperçu fixe ou lecteur HTML vidéo, position, volume et plein écran.
- `DetectionOverlay.vue` : calque indépendant acceptant plusieurs détections en coordonnées normalisées ; placé dans la surface réelle du média, y compris en présence de bandes latérales.
- `AnalysisSettings.vue` et `AnalysisStatus.vue` : réglages, actions et progression fictive.
- `frontend/src/data/analysis-preview.ts` : sources de démonstration, résultats fictifs, libellés, calcul de la surface et formatage du temps.
- `frontend/src/styles/analyse.css` : styles propres à cette page, préfixés `sa-`.

GlassPanel, FilterSelect, DemoDialog et les boutons du design system sont réutilisés. SymIcon reçoit uniquement les pictogrammes nécessaires au lecteur et aux réglages. Aucun composant de navigation supplémentaire n’est créé.

## Comportements

Le chevreuil et le renard sont des images fixes. La mention « IMAGE FIXE · LECTURE SIMULÉE » reste visible ; les contrôles font varier uniquement le temps de démonstration. Le fichier chevreuil affiché est un nom fictif.

Une troisième entrée lit réellement la vidéo locale d’écureuil `19136320-hd_1080_1920_50fps.mp4` (1080 × 1920, environ 6,83 secondes). Elle a été copiée depuis Downloads vers `frontend/src/assets/squirrel-local.mp4`, sans modifier l’original. Le bouton de lecture, le curseur et le volume pilotent l’élément HTML vidéo. Le calque reste fictif : il ne suit pas l’animal pendant sa lecture.

Le bouton Lancer l’analyse simule une progression pendant 1,75 seconde puis affiche « Analyse terminée — résultat de démonstration ». Les sélecteurs et le choix de vidéo sont désactivés pendant cette simulation. Changer les réglages réinitialise l’état. Préparer les recadrages ouvre une fenêtre informative ; aucune image n’est extraite ou enregistrée.

Toutes les propositions d’espèces, confiances et références de modèle sont fictives, y compris celles superposées au fichier réellement lu. Aucun appel API, traitement vidéo, modèle IA, upload ou stockage métier n’est ajouté. Les temporisateurs, observateurs de taille et écouteurs sont nettoyés en quittant la page.

Les exceptions ciblées de `.gitignore` conservent les données frontend et cet unique média de démonstration dans le dépôt ; les vidéos et données métier restent ignorées.

## Vérification et captures

Depuis `frontend/` :

```powershell
npm run dev -- --port 4173
npm run build
npm test
npx playwright test tests/e2e/analyse-design.spec.ts tests/e2e/symbiose-design.spec.ts tests/e2e/videotheque-design.spec.ts tests/e2e/dossiers-design.spec.ts tests/e2e/profile-logout.spec.ts
```

Les tests de la nouvelle page vérifient les deux colonnes à 1600 × 900, l’accessibilité, les interactions, les six rubriques, le plein écran, le mobile et le calque sur la vidéo portrait. Ils comparent aussi les trois pages existantes avant/après navigation : pixels hors éléments animés, puis géométrie, style et pictogrammes de chaque lien de la roue séparément. Le navigateur ne doit émettre aucune requête API ni erreur JavaScript.

Validation effectuée : 36 tests unitaires et 22 tests navigateur réussis. Compilation TypeScript/Vite et reconstruction du seul service Docker frontend réussies.

Les captures finales sans masquage sont conservées dans `output/symbiose/etape-4/` :

- `analyse-video-1600x900.png`
- `accueil-1600x900.png`
- `videotheque-1600x900.png`
- `mes-dossiers-1600x900.png`

## Image du chevreuil

Fichier final : `frontend/src/assets/analysis-deer.png`. Créé avec l’outil intégré `image_gen` à partir de la maquette Symbiose_Analyse. Il contient uniquement une photographie ; cadres, contrôles, textes et panneaux sont de vrais composants Vue/HTML/SVG.

Consigne exacte :

> Use case: precise-object-edit. Supporting reference: the supplied Symbiose Analyse video mockup. Create ONLY a standalone 3:2 camera-trap woodland photograph matching the photo inside its left video player. No dashboard, no glass cards, no controls, no green detection rectangle, no label, no text, no logo, no frames. The scene is dense European woodland at ground level, slender trunks, ferns, ivy and leafy undergrowth, brighter natural daylight from the left, neutral realistic trail-camera color and texture. A single roe deer is walking across the RIGHT-HAND third of the frame, slightly blurred by movement, with its full visible body concentrated approximately between x=68% and x=88% and y=40% and y=80%. The forest occupies the rest of the image with authentic detail and no other animal. Keep camera-trap realism, not a stylized illustration or polished wildlife portrait. This is a photo asset for a real HTML video player mockup, absolutely no baked-in UI of any kind.
