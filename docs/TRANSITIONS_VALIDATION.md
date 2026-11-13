# Validation des sept transitions — 12 novembre 2026

Le moteur est une étude spatiale continue avec géométrie provisoire et calques générés. La validation ci-dessous porte sur le fonctionnement, les états arrêtés et le repli ; elle ne vaut pas validation artistique définitive ni certification géographique.

## Périmètre visuel

Les états 0, 25, 50, 75 et 100 % sont capturés pour chacun des sept raccords. Les contrôles sont masqués pendant la capture du paysage, mais restent disponibles dans le DEBUG. Une image supplémentaire par raccord vérifie le rejeu à 50 %. La galerie est dans [output/symbiose/transitions/gpu/index.html](../output/symbiose/transitions/gpu/index.html) et les poses/cadences dans [report.json](../output/symbiose/transitions/gpu/report.json).

Les sept raccords utilisent une caméra réelle et un monde commun. L’interpolation est continue aux frontières, les effets sont purs et les pauses n’ajoutent pas de mouvement caché. La cohérence spatiale ne repose pas sur la superposition en opacité de deux photographies. Le repli est volontairement une version 2D à masques, identifiée dans son interface et sa [galerie séparée](../output/symbiose/transitions/fallback/index.html).

Les premières inspections ont révélé des collisions de caméra avec des couronnes, des berges trop grossières et une conversion de couleur manquante en sortie du post-traitement. Le corridor de passage, le maillage des berges et la conversion de sortie ont été corrigés. Les feuilles emploient des contours adoucis, les volumes nuageux une extinction de bord, et un îlot porte l’animal observé.

## Limites de finition

- Les arbres restent des troncs et branches procéduraux avec plans feuillus. Les angles rasants révèlent encore ces imposteurs ; les troncs demandent textures, détails et géométries de production.
- Les falaises possèdent une arche ouverte et une Aiguille distincte, mais leurs volumes restent schématiques. Elles évoquent Étretat sans reproduire une géométrie métrique ni une photographie du site.
- Les milieux aquatiques sont réunis par une ellipse. La réfraction est un effet d’écran, les rayons et la brume sont simulés ; aucune simulation volumétrique ou acoustique physique n’est revendiquée.
- Le cadre suit un chevreuil illustratif puis devient un schéma d’interface. Aucun score de confiance n’est fabriqué et aucun traitement métier n’est déclenché.
- Les 41 ressources de production déclarées absentes restent absentes. Les transitions peuvent être examinées comme études fonctionnelles ; elles ne sont pas marquées « finition cinématographique validée ».
- Firefox, Safari, mobiles physiques, vidéoprojecteur et lecteurs d’écran humains restent à examiner. Le build avertit du poids du chunk narratif Three.js/GSAP, chargé uniquement sur la landing.

## Protocole de performance

L’audit mesure chaque raccord pendant un aller-retour de 3,5 secondes, après 0,7 seconde d’amorce, en 1440 × 900. Il distingue les callbacks navigateur (`rafFps`) des images réellement rendues (`renderedFps`) et relève le p95 des intervalles, les appels de dessin, triangles, DPR, qualité et renderer. Les captures et arrêts ne sont pas des mesures de cadence.

Le moteur ne dessine plus lorsque le scroll et les contrôles sont immobiles. Le nombre de frames n’est donc pas un compteur tournant en arrière-plan. La qualité initiale est réduite sur mobile ou SwiftShader ; sur matériel, deux fenêtres de mouvement continu sous 36 fps abaissent le DPR. Une longue pause remet à zéro la fenêtre de mesure, sans déclencher une dégradation artificielle.

Le rejeu est comparé aux pixels. Le rapport conserve l’égalité exacte et le nombre de pixels différents. La tolérance de rasterisation est explicitement limitée à 0,01 % des pixels et huit niveaux par canal ; un dépassement fait échouer le script. Cette tolérance couvre les très petits arrondis GPU, sans accepter un autre cadrage ou une autre scène. Les mesures de cadence sont celles du navigateur et du rendu demandé, sans chronométrage GPU matériel par timer query.

## Mesure WebGL exécutée

Mesure du 12 novembre 2026, à 23 h 11 CET, contre `http://127.0.0.1:8080` (Nginx, Compose de base). Machine : AMD Ryzen 7 4800H, 15,4 Gio de mémoire utilisable. Chromium 156.0.8078.4 utilise **ANGLE / AMD Radeon intégré / D3D11**, et non la RTX mentionnée dans le contexte du projet. Résolution 1440 × 900, DPR 1, qualité standard pendant les sept mesures.

| Raccord | Images rendues/s | Intervalle p95 |
| --- | --- | --- |
| Forêt → Ciel | 60 | 16,7 ms |
| Ciel → Rivière | 60 | 16,7 ms |
| Rivière → Sous-marin | 60 | 16,7 ms |
| Sous-marin → Marais | 60 | 16,7 ms |
| Marais → Bocage | 60 | 16,8 ms |
| Bocage → Littoral | 60 | 16,7 ms |
| Littoral → Forêt nocturne | 60 | 16,7 ms |

Les appels de dessin relevés en fin de mesure vont de 22 à 57, et les triangles de 51 923 à 136 762. Les détails de chaque pose sont dans le rapport JSON. Ce résultat concerne ce monde provisoire, cet appareil et ce protocole ; les ressources de production plus détaillées devront être mesurées de nouveau.

**35 états WebGL et sept rejeux sont produits, sans erreur de console ou de réversibilité relevée.** Six rejeux ont exactement les mêmes pixels. Pour le cycle nocturne, seuls deux pixels diffèrent d’un niveau par canal sur 1 296 000 pixels ; cette différence de rasterisation a été examinée et respecte la tolérance annoncée. Elle n’est pas présentée comme une égalité binaire.

La [planche des 35 états](../output/symbiose/transitions/gpu/contact-sheet.png), la [galerie complète](../output/symbiose/transitions/gpu/index.html), le [DEBUG ouvert](../output/symbiose/transitions/gpu/debug-panel.png) et les [mesures brutes](../output/symbiose/transitions/gpu/report.json) sont conservés. Le repli a sa propre galerie de 35 captures et son rapport ; il ne fournit pas de mesure GPU fictive.

L’examen de l’ensemble des poses a aussi conduit à exclure les haies du lit de la rivière et du corridor de l’animal. Un test calcule les collisions de la trajectoire complète avec les instances réellement créées, sur 801 positions. L’état d’émergence à 75 % est dégagé. Le passage d’eau repose sur la surface du monde, sans seconde ligne de masque d’écran.

## Budget et limites de mesure

Le préchargement 3D porte sur huit calques alpha (8 817 846 octets) et le logo officiel. Les images principales ne sont chargées que par le repli ou la référence DEBUG. Les textures sont décodées avant révélation, puis conservées pendant la visite. Le rendu n’effectue aucun chargement progressif caché au milieu d’un raccord.

Le framebuffer intermédiaire est une texture couleur avec profondeur, à la résolution effective du canvas. Le shader d’eau ajoute une passe plein écran. Les arbres, haies, roseaux, poissons et nuages emploient des instances pour réduire les appels. Le DPR plafonne à 1,5 sur desktop et démarre à 0,65 en économie sur mobile/renderer logiciel. Les captures de performance n’utilisent pas le mode économie matériel.

## Vérifications exécutées

| Vérification | Résultat |
| --- | --- |
| `npm.cmd run test` | **127 tests réussis**, 24 fichiers, sans GPU |
| `npm.cmd run assets:check` | 16 ressources présentes et contrôlées, 41 absences explicites ; verrous de finition artistique inchangés |
| `docker compose config --quiet` | Réussi avec le fichier de base |
| `docker compose up -d --build --no-deps frontend` | Build TypeScript/Vite et démarrage Nginx réussis ; seul le frontend est recréé |
| `nginx -t`, `/`, `/connexion`, premier plan local | Configuration valide et HTTP 200 |
| Playwright sur l’image Nginx finale | **25 scénarios réussis** dans les quatre suites ciblées |
| Clavier, molette inverse, deux redimensionnements successifs | Vérifiés dans les parcours narratifs |
| Préférence système de mouvements réduits et réglage utilisateur | Vérifiés sur viewport mobile et dialogue du projet |
| Ressource alpha en erreur | Manque visible, géométrie et navigation conservées |
| WebGL indisponible et perte de contexte en cours de récit | Repli 2D vérifié, ancien canvas et annotations 3D libérés |
| Navigation hors landing puis retour | Un seul canvas réinstallé, pas de verrou de scroll restant |
| DEBUG | Sept raccords parcourus et rejoués, couche végétale masquée avec baisse effective des appels de dessin |
| Axe | Aucune violation dans les écrans desktop/mobile/dialogue couverts ; pas de certification de tous les états graphiques |
| Audit WebGL | 35 poses, 7 rejeux stables, zéro erreur relevée dans cet audit |
| Audit sans WebGL | 35 poses et 7 rejeux dans la tolérance, zéro erreur de script ; version 2D annoncée, couches 3D désactivées |

Les suites Playwright utilisent leurs **fixtures API**, y compris pour les sessions client/administrateur, l’analyse avec CSRF et la validation humaine. Elles vérifient les contrats et la non-régression du frontend ; elles ne constituent pas un test d’inférence ou d’intégration de la chaîne GPU. Les services backend, PostgreSQL, Redis et workers déjà actifs sont restés en place. Aucun fichier de leur implémentation n’est modifié.

Image frontend finale ayant passé les 25 scénarios : `sha256:d74402e7747ca0f9c66e81b69ac68725abfe26551a674fd4891c83d3c881b0bf`. Le frontend du Compose reste lancé sur 8080 ; le serveur Vite de contrôle a été arrêté.

Le moteur et les raccords sont donc **testables et fonctionnels comme études 3D**. La validation de finition cinématographique reste ouverte : silhouettes, matériaux, profondeur calibrée et ressources de production demandent encore du travail. Aucune approbation artistique humaine n’est déduite des tests automatisés.
