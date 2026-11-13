# Symbiose — animaux, matières et logo en particules

Mise à jour du 13 novembre 2026. Le build et le pack du jury incluent les modèles
locaux, sans téléchargement nécessaire à la présentation. L'inventaire vérifié
est [experience-models/inventory.json](../frontend/public/experience-models/inventory.json).

## Animaux réellement intégrés

| Source fournie | Livraison | Utilisation |
|---|---:|---|
| `3d assets/buse.glb` | 48 724 octets | Deux rapaces dans le chapitre aérien, trajectoire et mouvement d'ailes déterminés par le scroll |
| `3d assets/chevreuil.glb` | 1 929 592 octets | Forêt, zone humide et retour nocturne ; clips `Eating` / `Idle` du modèle |
| `3d assets/sanglier.glb` | 675 052 octets | Forêt diurne et nocturne |
| `3d assets/pigeon.glb` | 414 308 octets | Au sol dans la forêt et le bocage |
| `3d assets/poisson.glb` | 718 348 octets | Trois poissons immergés, encadrés « Poisson · espèce à confirmer », selon le choix de l'équipe |

Les cinq originaux totalisent **19 836 732 octets** ; les copies livrées
**3 786 024 octets** (−80,91 %). Images internes ramenées à 1024 px maximum,
JPEG qualité 86 pour les images opaques ; géométrie, squelette et clips utiles
préservés. Les originaux ne sont pas modifiés. Les animations non utilisées sont
retirées de la table des clips ; leurs buffers ne sont pas entièrement élagués.

Le modèle nommé « buse » contient des pièces nommées `Eagle_*` et une tête
blanche dans sa version fournie. La tête et la queue ont été recolorées en brun
pour une évocation de buse. Ce rapace reste stylisé. Ses pièces sont regroupées
en trois sous-ensembles pour éviter 24 draw calls par oiseau. Le pigeon est
étiqueté « Pigeon », sans supposer qu'il représente un pigeon ramier.

Les encadrés proviennent des volumes 3D projetés par la caméra. Ils sont masqués
hors champ ou derrière la caméra. Des étiquettes HTML décalées et des traits de
liaison limitent leur chevauchement. La mention **identifications non calculées**
reste visible. Ces modèles ne sont ni des observations de terrain ni une
inférence du classificateur. Aucune confiance numérique n'est inventée.

## Poly Haven réellement embarqué

Les fichiers ont été téléchargés via l'API publique ; métadonnées sources dans
`output/symbiose/nature-sources/`. Leur licence est
[CC0 selon Poly Haven](https://polyhaven.com/license).

- [Fern 02](https://polyhaven.com/a/fern_02) : petits massifs de sous-bois.
- [Rock Moss Set 01](https://polyhaven.com/a/rock_moss_set_01) : rochers groupés.
- [Tree Stump 01](https://polyhaven.com/a/tree_stump_01) : souches.
- [Forest Ground 04](https://polyhaven.com/a/forest_ground_04) : diffuse,
  normale OpenGL et rugosité du sol forestier.
- [Bark Brown 01](https://polyhaven.com/a/bark_brown_01) : diffuse,
  normale OpenGL et rugosité des troncs.

Les modèles sont convertis en GLB autonomes avec textures 1K embarquées.
Fougères, rochers et souches sont instanciés et séparés entre forêt diurne et
nocturne ; le secteur distant n'est pas rendu. Le matériau de sol forestier
s'atténue vers les autres milieux pour ne pas transformer le bocage en litière.
Le filtrage anisotrope est borné. Le paysage reste une reconstruction
illustrative : ces ajouts ne remplacent pas les arbres par une forêt scannée.

## Chargement et ressources

Les animaux sont préparés dans une fenêtre narrative de 18 secondes autour de
leur apparition et libérés lorsqu'ils en sortent. Les squelettes, matériaux,
géométries, textures et bitmaps ont une destruction explicite. Les décors communs
restent résidents pendant le parcours, puis sont détruits à sa fermeture.
Un cache borné des GLB compressés appartient à l'instance du monde et disparaît
sur son signal d'arrêt ; il évite les téléchargements répétés au retour arrière
sans garder tous les objets décodés sur le GPU.

Les [mesures de performance actuelles](SPATIAL_PERFORMANCE.md) quantifient le
chargement et le rendu. Les compteurs Three sont observables dans la télémétrie. Ils ne mesurent pas la
VRAM physique. Les [captures et mesures actuelles](../output/symbiose/spatial/release-gpu/index.html)
complètent les rapports antérieurs à ces modèles. Le mode 2D conserve le récit
et ses compositions ; il ne prétend pas afficher ces animaux en temps réel.

## Logo : amélioration livrée et fichier encore manquant

Le logo est maintenant échantillonné avec **7 200 points distincts**, répartis
sur son alpha en haute résolution, contre 320 tirages aléatoires auparavant.
Orientation verticale et proportions sont conservées. Le mot Symbiose est
lisible dans les captures contrôlées. La convergence reste réversible et liée
au scroll, sans boucle de rendu autonome à l'arrêt.

**Aucun SVG du logo n'a été trouvé dans le dépôt à cette livraison.** Le
résultat contrôlé utilise donc encore le PNG original du produit. Le chemin
exact du SVG a été demandé à l'équipe. Aucun SVG contenant simplement un PNG
encapsulé n'a été créé pour simuler ce remplacement.

Le pipeline sait embarquer un unique SVG dont le nom contient « logo » ou
« symbiose », déposé à la racine ou dans `3d assets/`. Il devient la source du
masque de particules via un décodage SVG à haute résolution. Ce raccordement
**n'a pas été validé avec le véritable fichier absent**. Le logo de l'interface
reste le fichier de marque existant.

## Reproduction

```powershell
# Depuis la racine, après installation de Pillow fixé dans requirements-assets.txt :
python frontend/scripts/prepare-spatial-assets.py
cd frontend
npm.cmd run build
node scripts/package-jury.mjs
```

Le script attend les téléchargements Poly Haven déjà archivés. Il ne fait aucun
appel réseau implicite et ne télécharge aucun modèle IA. Après ajout du SVG ou
du montage produit, reconstruire puis actualiser l'installation hors ligne.

Pour examiner les modèles isolément en développement :
`npm.cmd run dev -- --port 4173` depuis `frontend`, puis
`http://localhost:4173/tools/spatial-review.html`.
Le [montage de revue des huit modèles](../output/symbiose/nature-sources/model-review.png)
documente les poses et proportions des fichiers reçus.
