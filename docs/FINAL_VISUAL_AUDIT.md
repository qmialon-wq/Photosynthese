# Symbiose — audit visuel final

Revue du 13 novembre 2026, Chromium Windows, captures de production en 1440 × 900.
Les huit captures ont été ouvertes et examinées. Les galeries de raccords
complètent cette revue, sans constituer une validation artistique humaine.

Références : planche `Symbiose _ Voyage immersif du vivant normand.png`,
[bible artistique](art-direction/ART_BIBLE.md), manifeste ARQ, logo du produit.
La bible et les premiers rapports décrivent des jalons historiques ; le présent
rapport décrit l'intégration actuelle, sans lever leurs réserves sur les assets.

## Résultat de la comparaison

L'identité est reconnaissable : logo blanc exact, ivoire, verts profonds,
repères citron, grands titres éditoriaux, huit milieux et ancrages normands.
La narration répond aux cinq questions fournies et donne accès aux six critères
du règlement dans le carnet des sources. Les données documentées, bénéfices
attendus et perspectives restent explicitement distingués.

Le niveau photographique et la profondeur de la planche ne sont **pas atteints
par la reconstruction 3D**. Les troncs répétitifs, couronnes en plans, terrain
peu détaillé et masses littorales schématiques restent visibles. Le mode 2D
reprend les compositions d'intention générées : son image est plus proche de la
planche, mais ses raccords à masques ne sont pas une traversée géométrique.
Ni reconnaissance Awwwards, ni validation écologique ou artistique ne sont annoncées.

## Revue des huit chapitres

| Chapitre | Composition, cadrage, typo et lisibilité | Palette, profondeur, mouvement et assets : écart explicite à la planche |
|---|---|---|
| Forêt · problème | Titre à gauche, couloir central, silhouette d'observation discrète. Scrim et tailles de texte affinés ; fougères proches réduites pour libérer le cadre. Logo et navigation restent lisibles. | Verts différenciés, détail statique du sol et des écorces ajouté, sous-bois instancié. Les arbres en plans et branches droites restent répétitifs ; absence des feuillus et de la lumière volumétrique de référence. Ascension déterminée par le scroll. |
| Ciel · vision | Visée relevée pour dégager davantage de ciel et un horizon, titre en deux lignes et bénéficiaires compacts. Le gradient protège le contraste sur la brume claire. | Brume tempérée, continuité du cours d'eau ; terrain encore plat et bocage abstrait. La planche propose une vraie lecture aérienne des parcelles et des haies, non reproduite à ce niveau. Plongée continue, sans effet indépendant temporisé. |
| Rivières · données | Axe de rivière lisible derrière le diagramme HTML ; titre dominant, quatre sources et preuves repliables. Texte accessible hors canvas. | Eau adoucie et détail filtré pour réduire le moiré. Berges polygonales, végétation répétée et peu de reflets ; finesse photographique des ripisylves non atteinte. Immersion liée à la hauteur/position du parcours. |
| Monde immergé · perspectives | Zone textuelle calme, intitulé et statut « non opérationnelle » visibles. Le capteur schématique reste une illustration. | Eau vert gris, réfraction uniquement pendant l'immersion, poissons et bulles fondus avec celle-ci. Algues en rubans et paysage terrestre vu à travers l'eau restent artificiels ; aucun écosystème aquatique mesuré n'est démontré. |
| Zone humide · technique | Pipeline horizontal lisible, une explication active, légende locale/GPU. Plan d'eau bas, décor dans la partie droite. | Roseaux légers, profondeur par brume ; tiges uniformes, animal très simplifié, manque de strates végétales. L'apparition du décor distant a été avancée dans la brume. La zone humide riche de la planche reste une cible. |
| Prairie · démonstration | Hauteur intrinsèque du poster corrigée ; image, avertissement et choix local tiennent dans le cadre desktop. Les détails secondaires sont réduits sur écran court. Mobile reste déroulable. | La capture du manifeste est réelle et explicitement statique. Le bocage et le cadastre 3D restent schématiques ; la vidéo produit de 90 s est absente. Aucun film de navigation ou signal de test ne la remplace. |
| Littoral · impacts | Visée décalée : ouverture de l'arche et aiguille distincte à droite du texte. Les 12 alternatives et leur absence de mesure d'efficacité restent lisibles. | Craie et ciel neutralisés, silhouette rendue irrégulière et aiguille moins conique. Mais l'arche paraît encore construite en blocs et le rivage comporte une végétation invraisemblable : écart majeur au plan d'Étretat. Ce n'est pas une reconstruction géographique. |
| Forêt nocturne · équipe et suite | Citation, équipe ARQ, besoins et CTA entièrement visibles. Particules de marque réduites et décalées à droite, sans recouvrir la conclusion. | Désaturation et effacement des nuages progressifs, particules liées au scroll. Couronnes et étoiles restent stylisées, sans la matière ni le clair de lune de la référence. Le retour au vivant est narrativement complet, la finition de décor reste partielle. |

## Corrections transversales réalisées

- Suppression de la transition DOM `out-in` qui laissait une trame sans texte.
- Suppression du fondu du canvas et du mouvement autonome des pointillés.
- Navigation latérale allégée, contraste des petites légendes renforcé,
  scrim continu et hiérarchie de titres cohérente ; aucune police distante.
- Cadrage de la démonstration corrigé, légendes de preuve conservées.
- Une horloge partagée avec GSAP évite le plafonnement à 30 images/s introduit
  par une double programmation RAF. Pas de rendu WebGL continu à l'arrêt.
- Nuages, immersion, poissons, bulles et particules de conclusion sont évalués
  depuis la progression. Les caméras utilisent une interpolation continue ;
  navigation immédiate et passage volontaire d'animation restent disponibles.

## Ce que la revue ne valide pas

Les captures intermédiaires et les comparaisons de rejeu contrôlent des états
discrets ; elles ne prouvent pas l'absence de toute rupture perceptible entre
deux états, sur tout matériel. La recette ne remplace ni une répétition sur
vidéoprojecteur, ni la validation des 41 ressources de production encore
répertoriées absentes, ni la sélection artistique de l'équipe.

Les planches des raccords ont aussi été ouvertes sous forme de deux planches
contact de 35 états. Le panneau debug isole le décor : la narration y est
masquée pour examiner les trajectoires. Les captures des huit chapitres montrent
la composition avec le texte. Le repli 2D conserve des limites de masque
rectilignes visibles entre deux compositions ; il ne reproduit pas la
profondeur du raccord 3D.

Les huit masters et alphas restent des candidats. Les flags
`mainPlatesApproved`, `layeredScenesReady` et `transitionWorkAllowed` du manifest
artistique ne sont pas changés par cette livraison technique.

Captures : [chapitres WebGL](../output/symbiose/final/final-gpu/index.html),
[chapitres 2D](../output/symbiose/final/final-2d/index.html),
[raccords WebGL](../output/symbiose/final/transitions/gpu/index.html),
[raccords 2D](../output/symbiose/final/transitions/fallback/index.html).
