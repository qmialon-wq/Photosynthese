# Symbiose — reprise des décors

État du 13 novembre 2026. Cette reprise remplace les décors de la première
intégration des animaux. Les rapports dans `output/symbiose/spatial/` décrivent
la version précédente ; les nouvelles preuves sont dans
`output/symbiose/scenery/`.

## Changements visibles

- Sols : matériaux locaux de sous-bois et de prairie, variations à deux
  échelles, chemin plus clair et humidité près de l'eau. Les UV suivent
  l'échelle du terrain. Les berges rejoignent les collines progressivement.
- Forêt : vrais troncs, branches et feuillages texturés au premier plan.
  Les arbres éloignés utilisent quatre vues rendues depuis le modèle complet,
  avec interpolation entre les orientations. Les anciennes couronnes faites
  d'extraits de fougères et les grands panneaux de premier plan sont retirés.
- Bocage : haies courbes, arbres de tailles variées et touffes d'herbe 3D.
  Les placements préservent les passages de caméra et la rivière.
- Zone humide : tiges, feuilles effilées et massettes ; sous l'eau, rubans
  végétaux avec nervures, relief du fond et lumière réfractée.
- Eau : normales de vagues croisées perturbées par le vent, Fresnel, reflets
  lumineux chauds et écume de rive. Un reflet planaire commun aux deux plans
  d'eau montre réellement les arbres et les falaises.
- Étretat : arche courbe, aiguille effilée, géométrie érodée, strates et
  microrelief de roche, pied humide et sommet herbeux. Le nouveau cadrage
  expose l'ouverture de l'arche. La craie reçoit une lumière plus frontale.
  La mer continue derrière les falaises ; la rive de la forêt nocturne suit une courbe et une pente continue. le terrain nocturne éloigné
  s'efface progressivement dans cette vue pour éviter une paroi à l'horizon.
- Lumière : ciel utilisé comme environnement diffus, ombres directionnelles
  locales et brume assortie à l'horizon. La forêt nocturne conserve sa palette.
- Drone : suppression du grand quadrillage. Aucun nouveau modèle de drone
  n'est ajouté dans cette version.

Les identifications animales, le texte et le parcours restent illustratifs.
Les boîtes ne représentent pas une inférence exécutée dans la présentation.

## Sources embarquées

Les modèles et matériaux Poly Haven sont sous CC0. Il s'agit des fichiers
de production, pas d'images de prévisualisation récupérées sur leur site.

| Source | Usage |
|---|---|
| [tree_small_02](https://polyhaven.com/a/tree_small_02) | Arbres proches simplifiés et atlas de quatre vues rendu localement |
| [grass_medium_01](https://polyhaven.com/a/grass_medium_01) | Touffes 3D, variantes recentrées avant instanciation |
| [aerial_grass_rock](https://polyhaven.com/a/aerial_grass_rock) | Albedo des prairies et sommets herbeux |
| [rock_face_02](https://polyhaven.com/a/rock_face_02) | Détail de surface adapté à une craie claire par le shader |
| [forest_ground_04](https://polyhaven.com/a/forest_ground_04) | Sol forestier déjà acquis, désormais mélangé à plusieurs échelles |
| [fern_02](https://polyhaven.com/a/fern_02), [rock_moss_set_01](https://polyhaven.com/a/rock_moss_set_01), [tree_stump_01](https://polyhaven.com/a/tree_stump_01) | Sous-bois conservé et redistribué |

Les falaises sont une évocation construite en géométrie, pas un relevé
photogrammétrique d'Étretat. `rock_face_02` n'est pas présenté comme un scan
de la craie locale. Les fichiers et empreintes réellement livrés figurent dans
`frontend/public/experience-models/inventory.json`, également inclus au pack.

## Sobriété appliquée

Le modèle source de l'arbre dépasse deux millions de triangles. Le dérivé
proche contient environ 130 000 triangles, partagé entre les instances. Les
arbres éloignés sont des plans de deux triangles ; leur atlas WebP pèse
690 296 octets. Les maps de surface sont limitées à 1K, les touffes et plantes
sont instanciées, et les secteurs éloignés sont écartés du rendu.

Le reflet utilise une seule cible 768 × 768, sans multisampling ni récursion.
Il est inactif sur terre, sous l'eau et en mode économique. Les ombres utilisent
une carte 1024 × 1024, actualisée seulement lors d'un rendu utile. Une baisse
automatique de qualité supprime ombres et reflet, libère leurs cibles et réduit
le ratio de pixels. La cible d'environnement, les images décodées, les modèles,
les géométries et les matériaux sont détruits à la sortie de l'expérience.

Les vagues et lumières sont échantillonnées depuis la progression du récit :
pas de boucle permanente au repos ni de délai d'animation autonome. La fenêtre
de préchargement des anciennes photos de premier plan est retirée du rendu 3D.
Les huit compositions de secours restent disponibles sans WebGL. Aucun service
externe n'est nécessaire à l'exécution ; les acquisitions Poly Haven ont eu
lieu pendant la préparation des assets.

Les animaux suivent une fenêtre de chapitre avec anticipation et destruction
des instances sorties de cette fenêtre. Les ressources communes des décors
sont encore préparées au démarrage, puis conservées jusqu'à la sortie : le
chargement de l'ensemble du décor n'est pas entièrement progressif.

## Reproduction

Les sources téléchargées et métadonnées sont archivées dans
`output/symbiose/scenery-sources/`, les dérivés livrés dans le frontend.
Ils sont déjà prêts : ces commandes ne sont pas nécessaires au lancement.

```powershell
cd frontend
# Dépendances déjà fixées dans package-lock.json / requirements-assets.txt
node scripts/simplify-scenery.mjs
# Avec Vite actif sur 4173 : crée temporairement le modèle source puis le supprime
node scripts/bake-woodland.mjs
python scripts/prepare-scenery-assets.py
npm.cmd run build
```

La simplification d'un second LOD géométrique a été rejetée visuellement :
elle dénudait le feuillage. Ce fichier expérimental n'est pas embarqué.
Le rafraîchissement des animaux via `prepare-spatial-assets.py` conserve
l'inventaire des décors préparés séparément.

## Validation et limites

Les huit chapitres ont été capturés et examinés ; les 35 poses des raccords
ont également été inspectées en planche de contrôle. Une capture
inspectée ne vaut pas validation artistique de l'équipe. Les quatre vues des
arbres éloignés restent une approximation, notamment en survol. Les matériaux
ne transforment pas ce décor en reconstitution géographique exacte.

Le montage produit de 90 secondes reste à réaliser par l'équipe ; aucun
montage de démonstration fictif n'a été ajouté. Le vrai SVG du logo n'a pas
été trouvé dans les fichiers fournis lors de la précédente intégration.
