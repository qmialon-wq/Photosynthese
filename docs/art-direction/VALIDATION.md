# Validation de la livraison artistique

> Archive de la phase 2. La phase 3 ajoute des raccords sous forme d’études 3D provisoires : voir [la documentation actuelle](../EXPERIENCE_SYMBIOSE.md) et [sa validation](../TRANSITIONS_VALIDATION.md). Les manques et verrous artistiques consignés ici restent inchangés ; cette archive ne décrit pas l’état courant du moteur.

Contrôle du 12 novembre 2026. Cette validation concerne l’intégrité du pack, sa prévisualisation et la non-régression frontend. Elle ne remplace pas la validation artistique de l’utilisateur ou une expertise écologique et géographique.

| Contrôle exécuté | Résultat |
| --- | --- |
| Lecture des références | Manifeste de 13 pages, captures du produit, planche validée à la racine et éléments existants |
| Pack réellement produit | 8 masters et 8 premiers plans PNG, soit 16 fichiers et 31 003 548 octets |
| Dimensions réelles des rendus | 1672 × 941, consignées dans les manifests ; aucune résolution native 4K revendiquée |
| Transparence | Les 8 premiers plans possèdent des pixels alpha 0 et 255 ; inspection sur damier dans le navigateur |
| Logo | Source `symbiose-logo.png` intacte ; copie de galerie strictement identique par SHA-256 ; logo officiel affiché sur la landing |
| Ressources absentes | 41 emplacements, chacun avec chemin attendu, statut absent et brief détaillé ; aucun faux fichier vide |
| `npm.cmd run assets:check` | Réussi : fichiers, tailles, dimensions, alpha, empreintes, manifests, prompts et verrous de production |
| `npm.cmd run test` | 120 tests réussis dans 23 fichiers, sans GPU requis |
| `docker compose config --quiet` | Réussi avec le Compose de base |
| `docker compose build frontend` | Réussi, y compris `vue-tsc --noEmit` et Vite dans le builder Linux Node 22 |
| `nginx -t` et accès local | Configuration valide ; galerie et manifest servis en HTTP 200 sur le port 8080 |
| Playwright contre l’image Nginx finale | **22 scénarios réussis** : 3 de direction artistique, 4 du moteur narratif, 15 des parcours et sessions existants |
| Accessibilité automatisée | Contrôles axe sur desktop/mobile et écrans couverts par les tests ; aucune violation relevée sur ces périmètres |
| Réseau de la galerie | Aucun appel API ni ressource distante requis ; les 16 images sont décodées depuis le serveur local |

Image frontend testée : `sha256:b3c64d336a37c0255ea84cc5ab91a2a82205fbcddd8b71b3f8b4e297cb27b28d`.

Commande utilisée pour la passe finale, dans `frontend/` avec un conteneur frontend temporaire servant sur 8080 :

```powershell
$env:E2E_BASE_URL = 'http://127.0.0.1:8080'
npm.cmd run test:e2e -- art-direction.spec.ts narrative.spec.ts authenticated-workspace.spec.ts logo-navigation.spec.ts
```

Les scénarios métier utilisent leurs fixtures API. Le backend, PostgreSQL, les workers IA et leurs données ne sont pas démarrés ou modifiés pour cette vérification. Cette passe ne constitue donc pas un test d’inférence ou d’intégration de la pile complète.

Le contrôle de redimensionnement a aussi révélé un cache de hauteur de viewport GSAP : deux changements de taille suivis d’une navigation immédiate pouvaient empêcher d’atteindre la dernière pose. Le moteur rafraîchit désormais cette mesure avant les déplacements programmatiques et utilise la géométrie réelle de l’espace de scroll. Les assertions attendent la fin du lissage. Aucun nouveau raccord n’est ajouté par cette correction.

Le build conserve l’avertissement existant sur le poids du chunk narratif Three.js/GSAP. Le pack visuel d’environ 29,6 Mio est distribué dans l’image, mais n’est chargé que dans la galerie séparée ; il ne fait pas l’objet d’un préchargement sur les pages métier. Les formats optimisés et le budget d’un environnement animé feront partie de la production ultérieure.

## Prévisualisations conservées

- [Les huit compositions ensemble](../../output/symbiose/art-direction/contact-sheet.png).
- [Revue desktop](../../output/symbiose/art-direction/review-desktop.png) et [mobile](../../output/symbiose/art-direction/review-mobile.png).
- [Exemple de premier plan sur damier](../../output/symbiose/art-direction/alpha-coast.png).
- [Captures individuelles](../../output/symbiose/art-direction/scenes/) des huit scènes, sans mouvement de caméra simulé.
- [Inventaire CSV des 57 emplacements](../../output/symbiose/art-direction/asset-inventory.csv).

## Ce qui reste à valider

La reconnaissance d’Étretat comme évocation a été examinée visuellement : arche et Aiguille sont distinctes et entièrement visibles. La géométrie exacte et les détails écologiques ne sont pas certifiés. Les rendus ne sont pas des prises de vue authentiques ; les espèces et dispositifs montrés ne démontrent aucune observation ni capacité logicielle supplémentaire.

Les contours d’alpha demandent encore une revue fine avec des fonds reconstruits. Fonds propres, profondeurs calibrées, géométries, passes atmosphériques, pré-rendus et vidéo produit sont absents. Safari, Firefox, mobiles physiques, lecteur d’écran humain, projection et performance des futurs environnements animés restent hors de cette passe.

Les trois verrous `mainPlatesApproved`, `layeredScenesReady` et `transitionWorkAllowed` restent à `false`. Les compositions attendent la validation humaine ; aucune nouvelle transition ni activation des six scènes prévues n’est entreprise.
