# Symbiose — performance après intégration 3D

> Nouvelle livraison des decors : **31c94db9b955178c**. Voir [la reprise des decors et sa recette](SCENERY_REWORK.md). Les mesures et captures ci-dessous sont conservees comme historique de la version precedente.


Production du 13 novembre 2026, révision **28f7ee22a2222aee**.
Mesure réelle : Chromium 156.0.8078.4, Windows, AMD Ryzen 7 4800H with Radeon Graphics, 15.42 Gio RAM.
Viewport 1440 × 900, renderer **ANGLE (AMD, AMD Radeon(TM) Graphics (0x00001636) Direct3D11 vs_5_0 ps_5_0, D3D11)**.
Il s'agit de l'AMD intégré ; la RTX 3050 n'est pas utilisée dans cette mesure.

| Raccord | Cadence de nouveaux rendus (FPS) | P95 entre rendus (ms) | Draw calls en fin d'échantillon |
|---|---:|---:|---:|
| forest → sky | 54.6 | 33.4 | 53 |
| sky → rivers | 58.9 | 16.8 | 35 |
| rivers → underwater | 58.9 | 16.8 | 28 |
| underwater → wetland | 53.6 | 16.8 | 24 |
| wetland → meadow | 57.9 | 16.8 | 29 |
| meadow → coast | 58.9 | 16.8 | 26 |
| coast → night-forest | 53.2 | 33.3 | 19 |

Protocole : sept allers-retours de 3,5 s, 700 ms de mise en mouvement exclues, mesures exécutées séparément des builds et des autres navigateurs de test.
Le PC n'est pas isolé des autres applications : ce n'est pas un benchmark contrôlé.
**60 FPS constants ne sont pas validés.** Les résultats ne sont pas extrapolés à d'autres GPU ni à la salle de projection.
Une seconde passe par les contrôles debug des raccords mesure **42–56 rendus/s**. Les deux protocoles et les variations de charge du PC doivent rester visibles dans l'interprétation ; la première plage ne constitue pas une cadence garantie.

- Scène prête en **3432 ms**, observation unique.
- Sur 2,2 s immobiles : **0 nouveau rendu WebGL**.
- Parcours complet de capture et d'aller-retour : **42948072 → 17500774 octets transférés**, **91 → 65 requêtes**, avant/après le cache des GLB encodés. Le parcours inclut des passages répétés ; ces chiffres ne décrivent pas seulement le premier chargement.
- Cache hors ligne installé : **15705353 octets**, **46 ressources**, vidéo produit absente. Serveur et README sont supplémentaires au cache.
- Tas JS observé à la fin : **76600000 octets**. Ce compteur ne comprend pas toutes les allocations natives, buffers ou textures du pilote.
  Avant le cache, la photographie correspondante était de 37300000 octets. Le cache échange une rétention CPU bornée contre des transferts évités ; les deux photographies n'ont pas un cycle de GC contrôlé et ne prouvent pas un gain de mémoire.

| Pose | Draw calls | Triangles | Textures Three | Animaux encadrés visibles |
|---|---:|---:|---:|---:|
| forest | 54 | 410009 | 30 | 3 |
| sky | 34 | 149182 | 30 | 2 |
| rivers | 27 | 135640 | 19 | 0 |
| underwater | 25 | 146386 | 24 | 3 |
| wetland | 31 | 134499 | 30 | 1 |
| meadow | 27 | 138741 | 28 | 2 |
| coast | 22 | 55937 | 21 | 0 |
| night-forest | 31 | 303877 | 30 | 2 |

Les textures décomptées incluent celles des GLB, matériaux et squelettes. Le champ estimatedImageBytes de la télémétrie porte seulement sur les images du préchargeur historique ; il ne représente pas tout le nouveau décor.
**Aucune mesure de VRAM physique, d'énergie ou d'émissions carbone n'a été effectuée.**
Le contrôle de retour à la forêt teste la libération des textures de squelette après plusieurs changements de milieu ; ce n'est pas un test d'endurance de plusieurs heures.

Les stratégies mises en œuvre sont décrites dans [Animaux et matières](SPATIAL_ASSETS.md) : copies 1K, regroupement du rapace, instanciation et secteurs, chargement anticipé, éviction des objets décodés, cache compressé borné, destruction à l'arrêt, DPR adaptatif et repli 2D.
Le diagnostic logiciel antérieur mesurait moins de 10 FPS ; ce moteur bascule donc automatiquement vers la 2D.

[Rapport brut](../output/symbiose/spatial/release-gpu/report.json) · [captures des huit chapitres](../output/symbiose/spatial/release-gpu/index.html).
