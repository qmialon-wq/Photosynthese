# Symbiose — bilan de livraison finale

Livraison locale du 13 novembre 2026, revision **31c94db9b955178c**. Le build est produit et servi par Nginx.
L'entrée autonome du jury est **http://localhost:8080/jury/** ; elle démarre
indépendamment de l'authentification et des services métier.

Les matériaux, les végétaux, la lumière, l'eau et les falaises ont été repris.
La validation artistique complète reste **partielle** : le décor hybride
n'atteint pas partout la profondeur photographique de la planche. La vidéo produit de 90 s doit encore
être réalisée par l'équipe, comme convenu. Aucune qualité Awwwards n'est annoncée.

## Livrables

| Livrable | Accès |
|---|---|
| Reprise actuelle des decors | [Materiaux, lumiere, eau, falaises, mesures et tests](SCENERY_REWORK.md) |
| Build de production | `frontend/dist/` et image Docker locale `biosentinelle-frontend` |
| Pack portable | [Symbiose-jury-2026.zip](../output/symbiose/Symbiose-jury-2026.zip) |
| README et lancement | [Frontend](../frontend/README.md) ; [README du dépôt](../README.md) |
| Guide du présentateur | [Préparation, commandes, incidents](PRESENTER_GUIDE.md) |
| Audit visuel par chapitre | [Comparaison à la planche et écarts](FINAL_VISUAL_AUDIT.md) |
| Assets | [Inventaire et provenance](FINAL_ASSETS.md) |
| Ajouts 3D | [Animaux, Poly Haven, particules et SVG manquant](SPATIAL_ASSETS.md) |
| Performance et sobriété | [Mesures de la reprise des decors](SCENERY_REWORK.md), [mesures des premiers GLB](SPATIAL_PERFORMANCE.md), [audit initial](PERFORMANCE_SYMBIOSE.md) |
| Tests | [Exécutions et périmètres réels](FINAL_TEST_REPORT.md) |
| Secours fixe | [PDF de huit pages](../output/symbiose/final/secours-symbiose.pdf) |
| Captures | [Chapitres 3D](../output/symbiose/final/final-gpu/index.html), [chapitres 2D](../output/symbiose/final/final-2d/index.html), [raccords 3D](../output/symbiose/final/transitions/gpu/index.html), [raccords 2D](../output/symbiose/final/transitions/fallback/index.html) |
| Captures precedentes avec les animaux | [Huit chapitres courants](../output/symbiose/spatial/release-gpu/index.html), [raccords courants](../output/symbiose/spatial/transitions/gpu/index.html) |
| Captures actuelles | [Huit decors](../output/symbiose/scenery/release-gpu/index.html), [avant/apres](../output/symbiose/scenery/comparison.html), [raccords](../output/symbiose/scenery/transitions/gpu/index.html) |

## Lancement

Avec l'installation Docker existante, depuis la racine :

```powershell
docker compose up -d --build --no-deps frontend
```

Ouvrir `/jury/`. Pour éviter entièrement WebGL, ouvrir
**http://localhost:8080/jury/?render=2d**. Ce mode conserve les huit compositions,
les sources et le lecteur local ; il est actuellement plus proche de l'intention
visuelle de la planche. Les moteurs logiciels détectés y basculent automatiquement.

Sans Docker ni backend : décompresser le pack, puis, depuis son dossier :

```powershell
node serve-jury.mjs .
```

Ouvrir **http://localhost:8088/jury/**. Node.js doit être installé ; aucune
installation npm n'est nécessaire pour servir ce pack. Dans **Préparation du
jury**, installer les ressources locales et attendre le message de réussite.
Le cache, le profil de navigateur et l'origine doivent être conservés. Un
double clic sur `index.html` ne remplace pas le serveur HTTP local.

## État des critères

| État | Périmètre |
|---|---|
| **Terminé et testé** | Build typé, huit chapitres et sources, cinq modèles animaux locaux, encadrés projetés et réversibles, libération des textures de squelette, décors et matériaux Poly Haven, navigation et retour arrière, clavier, modes exploration/présentation, mouvements réduits, repli après perte WebGL, sélection/lecture/pause d'un fichier vidéo de test, plein écran Chromium, redimensionnement, point de reprise/relance/passage d'animation, installation et rechargement hors ligne avec les GLB, pack sans backend, lien réel vers la page de connexion. Détails et réserves dans le rapport de tests. |
| **Terminé mais non testé** | Raccordement d'une piste WebVTT locale sur le montage final, branche de chargement du vrai SVG absent et adaptation de qualité sur un autre appareil physique lent ; logique de qualité vérifiée en tests, pas de campagne multi-GPU. |
| **Partiellement réalisé** | Finition des décors 3D face à la planche, sensation de profondeur et naturel d'Étretat ; objectif constant de 60 FPS ; critère de démonstration réelle, actuellement limité à une capture sourcée et au lecteur prêt. |
| **Non réalisé** | Création du montage produit de 90 s, production des 41 ressources artistiques encore absentes, validation artistique de l'équipe, répétition avec vidéoprojecteur et montage final, essais humains au lecteur d'écran, recettes Firefox/Safari et endurance de plusieurs heures. |

## Limites restantes

- Les contenus racontent problème, solution, données, technique, bénéfices,
  équipe et besoins. Les cinq questions fournies et les six critères du jury
  sont mappés dans le carnet. Cela ne garantit pas une validation du jury.
- L'annexe du règlement juxtapose une formulation emploi/formation et une note
  biodiversité ; cette ambiguïté est conservée dans le carnet, sans réécriture.
- Les 12 alternatives documentées ne sont pas des mesures d'efficacité
  écologique. Les scènes, animaux et capteurs sont illustratifs. L'aquatique
  reste une perspective, pas un modèle fonctionnel annoncé.
- La mesure GPU identifie l'AMD intégré utilisé par Chromium, pas la RTX 3050.
  Le PC n'était pas isolé des autres applications ; les FPS ne sont pas une
  promesse pour la salle. Les métriques mémoire des images sont des estimations,
  pas une mesure de VRAM physique ou d'énergie.
- Le hors ligne porte sur le pitch. L'application finale, ses comptes, API,
  modèles et tâches GPU exigent les services habituels. Aucun cache métier ni
  résultat simulé ne permet de prétendre à une inférence hors ligne du pack.
- Un fichier vidéo choisi temporairement reste local mais doit être sélectionné
  à nouveau après rechargement. Pour la séance, embarquer le montage au build,
  ses sous-titres, reconstruire puis actualiser et retester l'installation.
- Le PDF constitue un support fixe, sans vidéo ni simulation d'interactivité.
- Les cinq animaux GLB et les matériaux Poly Haven sont intégrés. Le vrai SVG du
  logo reste à fournir ; l'amélioration des particules contrôlée emploie encore
  le PNG original, comme indiqué dans la note d'intégration.

Les rapports initiaux de direction artistique, de transitions et de pitch sont
conservés comme historique. Les présents rapports décrivent l'état de cette
livraison et ne transforment pas leurs validations en approbations acquises.
