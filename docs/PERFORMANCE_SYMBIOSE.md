# Symbiose — performance et sobriété

Mesures du 13 novembre 2026, **Chromium 156.0.8078.4**, Windows 11, **1440 × 900**.
CPU : AMD Ryzen 7 4800H with Radeon Graphics ; RAM : 15.42 Gio.
Renderer réel : "ANGLE (AMD, AMD Radeon(TM) Graphics (0x00001636) Direct3D11 vs_5_0 ps_5_0, D3D11)".
**La RTX 3050 n'a pas servi à ces captures.**

## Protocole

Sept allers-retours de 3,5 s, avec 700 ms de démarrage exclues : cadence RAF et intervalles entre nouveaux rendus WebGL comptés séparément.
Une autre passe capture cinq états par raccord, revient en arrière et compare les pixels à 50 %.
Les délais de mesure ne pilotent aucune animation du site.
Les mesures de cadence sont exécutées séparément des builds et des autres audits navigateur.
Le PC reste celui de l'utilisateur, avec d'autres applications ouvertes : sa charge GPU et système n'est pas isolée.
Baseline et finale ne constituent donc **pas un benchmark contrôlé prouvant un gain de FPS**.
Les changements de cadrage et de décor modifient aussi la charge.

| Parcours | Baseline rendu (FPS) | Finale rendu (FPS) | P95 rendu final (ms) | Logiciel diagnostic (FPS) |
|---|---:|---:|---:|---:|
| forest → sky | 60.0 | 51.0 | 33.4 | 4.8 |
| sky → rivers | 60.0 | 53.9 | 33.4 | 6.5 |
| rivers → underwater | 60.0 | 60.0 | 16.8 | 4.7 |
| underwater → wetland | 60.0 | 40.7 | 50.1 | 7.9 |
| wetland → meadow | 60.0 | 51.8 | 33.4 | 7.1 |
| meadow → coast | 60.0 | 56.5 | 16.8 | 6.8 |
| coast → night-forest | 60.0 | 40.7 | 50.0 | 8.8 |

**60 FPS constants ne sont pas validés.** La finale atteint ponctuellement 60 FPS ; la seconde passe de raccords mesure 47–56 rendus/s.
Le défaut intermédiaire d'une double programmation RAF à environ 30 FPS est corrigé : le rendu partage désormais l'horloge GSAP.
SwiftShader reste insuffisant même en éco (DPR 0,65 et végétation réduite).
La version livrée libère donc automatiquement les moteurs logiciels pour continuer en 2D.
Seul le paramètre diagnostique "?render=software" conserve ce moteur pour reproduire ses mesures.

## Chargement et ressources

- Scène prête : baseline **1283 ms**, finale GPU **2061 ms**, 2D **1120 ms**. Mesures uniques, aucune amélioration de démarrage ni score Lighthouse revendiqué.
- Transfert cumulé du parcours public : **14099731 → 7271227 octets**, **20 → 50 requêtes**. Le chargement progressif répartit les requêtes. 2D : 3244837 octets. Le bundle public inclut son contexte applicatif ; l'entrée jury évite l'authentification.
- Cache jury : **5460554 octets**, 31 ressources, vidéo absente. [Inventaire](FINAL_ASSETS.md).
- Scène immobile pendant 2,2 s : **0 nouveau rendu WebGL**.
- Sur huit poses : 2 à 4 images résidentes, jusqu'à 6 textures Three incluant la réfraction. Estimation maximale bitmaps + mipmaps : **19 660 800 octets**. Ce n'est pas une mesure de VRAM physique et cela exclut framebuffer, géométrie et allocations du pilote.
- Tas JS observé en fin de parcours : 19300000 octets (baseline 17100000). Photographie ponctuelle, sans test d'endurance de plusieurs heures ni preuve d'absence de fuite.

| Pose | Draw calls baseline | Draw calls finale | Triangles finale |
|---|---:|---:|---:|
| forest | 57 | 46 | 134890 |
| sky | 49 | 40 | 147508 |
| rivers | 47 | 39 | 136712 |
| underwater | 41 | 35 | 136750 |
| wetland | 36 | 36 | 133473 |
| meadow | 18 | 25 | 114257 |
| coast | 22 | 22 | 55937 |
| night-forest | 12 | 12 | 39928 |

Les draw calls ne diminuent pas partout : sous-bois et visibilité anticipée enrichissent certains plans.
Ce tableau ne démontre pas une réduction uniforme du coût de scène.

## Choix réellement implémentés

- WebP optimisés : **−87,14 %** sur 17 images, masters préservés ; alphas vérifiés à la taille livrée et RGB avec pertes.
- Ciel partagé et fenêtre de premiers plans voisins ; préchargement du suivant. Les cartes hors fenêtre, textures, matériaux, géométries et bitmaps sont libérés. Chargements dédupliqués, résultat obsolète protégé des textures encore attachées.
- Une passe sur terre, deux uniquement dans l'eau ; cible intermédiaire libérée à la sortie. Végétation instanciée ; éléments éloignés masqués ; détail de matière statique sans texture ni passe ajoutée.
- DPR standard plafonné à 1,5 ; éco initial à 0,65. Deux fenêtres lentes successives réduisent la résolution en standard. Logique testée ; aucune garantie de 60 FPS universels.
- Pas de rendu GPU autonome à l'arrêt, onglet caché ou carnet ouvert. Tous les effets suivent la progression narrative, sans horloge décorative infinie. Destruction au départ de la page.
- "prefers-reduced-motion" fixe les points de vue et désactive la lecture animée. Textes HTML, sources locales et navigation clavier restent disponibles. "?render=2d" évite entièrement le chargement et la création du contexte WebGL.
- Vidéo manuelle, "preload=none", muette au départ, pause au changement de chapitre et à l'ouverture des sources. Traitement du vrai montage absent encore à tester.
- Aucun CDN ni police distante indispensable. Gzip Nginx ; cache installé explicitement et limité au jury, sans cache de session ou de données métier.

Pas de mesure électrique, carbone, de temps GPU par timer query ou de VRAM physique effectuée.
Aucune économie énergétique chiffrée annoncée.

Rapports bruts : [baseline](../output/symbiose/final/baseline-gpu/report.json), [GPU](../output/symbiose/final/final-gpu/report.json), [logiciel](../output/symbiose/final/final-software/report.json), [2D](../output/symbiose/final/final-2d/report.json), [raccords GPU](../output/symbiose/final/transitions/gpu/report.json).
