# Symbiose — rapport des tests exécutés

> Nouvelle livraison des decors : **31c94db9b955178c**. Voir [la reprise des decors et sa recette](SCENERY_REWORK.md). Les mesures et captures ci-dessous sont conservees comme historique de la version precedente.


Recette locale du 13 novembre 2026. Production finale : **28f7ee22a2222aee**, Nginx sur 8080, pack autonome sur 8088.
Le build TypeScript/Vite a été exécuté localement et dans Docker. Seul le frontend a été reconstruit.
L'avertissement de chunk Three supérieur à 500 ko reste présent ; ce chunk est chargé à la demande et évité par la 2D forcée.

## Exécutions réelles

| Exécution | Résultat |
|---|---|
| Suite Vitest, 28 fichiers, deux workers et timeout 15 s | 143/143 réussis, 0 échec |
| Contrôles ciblés du cache GLB et des assets/encadrés/particules | 5/5 réussis |
| Première recette complète, 34 scénarios | 32 réussis, 2 échecs ; deux nouveaux tests visaient le début du chapitre avant l'arrivée des animaux |
| Recette finale des scénarios concernés après cache et correction des poses de test | 19 réussis, 0 échecs, 0 ignoré, 0 instable |
| Pack autonome final | Rechargement hors ligne : true ; huit chapitres ; sources locales ; plein écran natif Chromium : true ; sortie du plein écran ; redimensionnement ; lien réel vers http://localhost:8080/connexion |
| Audit visuel/métriques de production, huit chapitres et sept allers-retours | 0 erreur JavaScript ; 0 requête externe |
| Raccords actuels avec les animaux | 35 poses capturées ; 7/7 rejeux dans la tolérance ; 1 strictement identique ; 0 erreur |
| Préparation Python | Exécution réelle du convertisseur, contrôle des SHA-256, compilation Python et Ruff 0.9.10 check/format exécutés |

La première recette complète et la dernière recette ciblée sont deux exécutions distinctes : aucune commande unique de 34 scénarios n'est annoncée entièrement verte. Les 32 scénarios existants étaient verts avant la dernière optimisation du cache. La recette ciblée reprend le récit, la vidéo, le jury et les deux scénarios 3D ajoutés.

## Périmètre des dix vérifications demandées

| Vérification | Ce qui a réellement été exécuté |
|---|---|
| Démarrage | Entrée publique et entrée jury ; absence d'appel métier dans le jury ; erreur WebGL et bascule logicielle vers 2D |
| Scroll complet | Parcours des huit chapitres par progression contrôlée et positions représentatives, sept allers-retours instrumentés ; molette native dans des scénarios séparés |
| Retour arrière | Molette, navigation de chapitre, poses réversibles et encadrés aux mêmes positions ; nouveaux GLB rechargés après éviction |
| Clavier | Flèches, Page précédente/suivante, Début/Fin, Espace, Tab, Échap, focus du carnet ; touches natives conservées sur le lecteur et les formulaires |
| Vidéo | Fichier VP8 local de test réellement décodé et lu, contrôles manuels, pause, carnet, molette du panneau interne, libération au départ ; erreur d'un fichier illisible |
| Plein écran | Entrée et sortie natives dans Chromium sur le pack autonome ; scénario de refus de l'API également testé |
| Redimensionnement | Plusieurs viewports desktop ; conservation de position ; mobile simulé 390 × 844, sans appareil mobile physique |
| Exploration | Défilement natif et interruption de lecture ; aucune boucle GPU à l'arrêt |
| Présentation | Arrêts, navigation immédiate, passage d'animation, reprise après rechargement et relance |
| Lien final | Attribut attendu, clic réel vers la page de connexion de l'application disponible sur 8080 |

Les scénarios métier utilisent des réponses API/session de test ; ils ne prouvent pas une inférence GPU ni une analyse écologique. Le signal vidéo validé est dans tests/fixtures et n'est jamais embarqué comme démonstration du produit.
Les contrôles Axe exécutés portent sur les états desktop/mobile/carnet couverts ; ils ne constituent pas une certification WCAG complète.

## Incidents corrigés ou distingués

- Transition DOM laissant un texte momentanément absent, cadrage trop haut du poster et programmation à 30 FPS : corrigés avant les captures finales.
- Molette interne pouvant perdre la frontière exacte du chapitre vidéo : corrigée, puis testée avec un vrai fichier décodable.
- Génération vidéo MediaRecorder instable dans le test : remplacée par un fichier VP8 local dont la lecture a été contrôlée séparément, sans changer le produit pour faire passer le test.
- Un contrôle unitaire attendait encore les anciens poissons en cônes : il vérifie désormais leur remplacement et le fondu des bulles ; les vrais poissons sont contrôlés en navigateur.
- Un timeout de 5 s lors du contrôle des PNG sous forte charge : suite rejouée avec deux workers et 15 s. Le résultat final est celui indiqué plus haut.
- Un ancien lancement concurrent de deux runners partageant leur dossier d'artefacts a produit une erreur de trace ; les recettes de livraison utilisent des dossiers distincts et un seul worker.

## Non exécuté / limites

Véritable montage produit de 90 s et ses VTT absents ; vrai SVG du logo absent ; validation naturaliste des modèles ; vidéoprojecteur ; Firefox/Safari ; lecteur d'écran humain ; appareil mobile physique ; campagne multi-GPU ; endurance de plusieurs heures ; mesure de VRAM ou d'énergie ; inférence métier réelle dans le pack.
Les captures de raccords historiques précèdent les modèles ; une nouvelle passe de 35 poses et sept rejeux les inclut. Les comparaisons acceptent au maximum 8 niveaux par canal et 0,01 % de pixels modifiés. Elles ne prouvent pas l'absence de tout saut perceptible entre deux états échantillonnés. La galerie courante de chapitres montre également les animaux ; les rapports bruts identifient chaque exécution et ne doivent pas être mélangés.

## Preuves

[Unitaires](../output/symbiose/spatial/tests-unit.json), [cache ciblé](../output/symbiose/spatial/tests-unit-cache.json), [recette complète](../output/symbiose/spatial/tests-production.json), [recette finale ciblée](../output/symbiose/spatial/tests-release.json), [pack](../output/symbiose/final/package/report.json), [captures actuelles](../output/symbiose/spatial/release-gpu/index.html), [35 poses des raccords](../output/symbiose/spatial/transitions/gpu/index.html).
