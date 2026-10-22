# Package `biosentinelle_vision`

Le [guide d'inférence](INFERENCE.md) décrit le couple MegaDetector testé,
le provisionnement des poids, les diagnostics image, l'API asynchrone,
les seuils indépendants et le schéma des rapports vidéo v2.

Le [guide d'entraînement](TRAINING.md) décrit les runs reprenables, AMP,
l'accumulation, les métriques SQL/JSON et l'interface distincte pour le détecteur.

Extraction modulaire du notebook historique V3. La correspondance des **27 cellules**
et les divergences fonctionnelles sont dans [NOTEBOOK_MIGRATION.md](NOTEBOOK_MIGRATION.md).
Le notebook original reste à la racine et n'est pas exécuté par ce package.

Les commandes Make `prepare-training`, `train`, `analyze` et `watch`, leurs prérequis et dossiers
sont décrits dans le [guide principal](../../README.md#entraînement-et-vidéos-annotées-avec-make).
Elles correspondent aux commandes CLI du même nom (`train --check-only` pour le
diagnostic). Les modèles sont chargés uniquement sur demande. Le fichier
Compose ML construit une image supplémentaire complète ; l'image CPU de base
conserve ses dépendances légères.

## Classes et compatibilité

Après confirmation utilisateur, conserver les **10 classes réellement présentes
dans le code**, sans ajouter le merle mentionné dans le texte :

```text
0 chevreuil, 1 sanglier, 2 buse, 3 pigeons, 4 martres,
5 renards, 6 blaireaux, 7 chouette, 8 geai, 9 faisans
```

Le manifeste embarqué `manifests/classes-v3-10.json` porte la version `v3-10.1`.
Les alias « pigeon ramier », « martre », « faisan », etc. reconnaissent les noms
locaux sans modifier les identifiants historiques. Les checkpoints V3 à dix sorties
sont acceptés seulement si leur liste `classes` a exactement cet ordre ; les nouveaux
checkpoints enregistrent aussi la version du manifeste. Aucune permutation automatique.

## CLI CPU dans Docker

Depuis la racine du monorepo, construire l'image vision mise à jour :

```sh
docker compose build vision
docker compose run --rm vision biosentinelle-vision --help
docker compose run --rm vision biosentinelle-vision inventory /storage/datasets --output /storage/results/vision/inventory.json
docker compose run --rm vision biosentinelle-vision extract-frames --inventory /storage/results/vision/inventory.json --output-dir /storage/results/vision
```

Placer explicitement les vidéos dans `data/datasets/`, ou fournir un montage
Docker additionnel en lecture seule. `make classify-videos` copie les vidéos
historiques par espèce. `inventory` calcule les empreintes SHA-256, vérifie le décodage de
la première image et sépare les groupes avant extraction. `--no-probe` désactive
uniquement le contrôle vidéo, pas les empreintes. Les espèces inconnues ou
ambiguës restent dans le manifeste avec `species_candidate=null`.

`extract-frames` produit des JPEG sous `frames/<video_id>/` et `frames.json`.
Les clés image sont relatives à la racine de stockage. L'inventaire conserve la
racine du dataset : pour le réutiliser dans un autre environnement, adapter
explicitement `dataset_root` au montage local. Les fichiers source sont revérifiés
par empreinte avant extraction. Les échecs sont dans `issues`, même si d'autres
vidéos ont réussi. Les fichiers manifestes sont écrits atomiquement.

Codes de retour CLI : 0 succès ; 1 configuration/entrée invalide ; 2 résultat
partiel ou aucun élément exploitable. Un manifeste partiel est conservé pour diagnostic.

## Installation Python locale

Python 3.11 à 3.13 (3.12 recommandé), dans un environnement dédié ; l'ancien
venv du monorepo peut utiliser une version différente. Pour les outils CPU :

```sh
python -m pip install -r workers/vision/requirements.txt
python -m pip install --no-deps -e workers/vision
biosentinelle-vision inventory "video datathon" --output data/results/vision/inventory.json
biosentinelle-vision extract-frames --inventory data/results/vision/inventory.json --output-dir data/results/vision
```

Les mêmes commandes sont accessibles via `python -m biosentinelle_vision`.
Sous Linux, OpenCV requiert `libgl1` et `libglib2.0-0` ; les images concernées les
installent. Un seul fournisseur OpenCV est utilisé (`opencv-python==4.11.0.86`),
également déclaré par MegaDetector : ne pas installer simultanément le paquet
`opencv-python-headless` qui écrit lui aussi dans `cv2`.

## Détection et classification réelles, facultatives

Les images par défaut installent le package CPU et **ne contiennent pas les
dépendances ML optionnelles**, même si l'image GPU préexistante contient PyTorch.
Dans un environnement Python dédié, installation explicite de la pile ML verrouillée :

```sh
python -m pip install -r workers/vision/requirements-ml.txt
python -m pip install --no-deps -e workers/vision
biosentinelle-vision detect --frames data/results/vision/frames.json --storage-root data/results/vision --weights data/models/md_v5a.0.0.pt
```

Cette installation télécharge des **bibliothèques**, potentiellement volumineuses ;
elle ne provisionne aucun poids. La commande exige un fichier `.pt` déjà présent,
issu d'une source de confiance. Aucun nom tel que `MDV5A` n'est transmis au chargeur
comme raccourci téléchargeable, et aucun détecteur COCO de remplacement n'est prévu.
Les signatures utilisées sont celles du
[chargeur officiel MegaDetector](https://github.com/agentmorris/MegaDetector/blob/main/megadetector/detection/run_detector.py)
et de son
[détecteur PyTorch](https://github.com/agentmorris/MegaDetector/blob/main/megadetector/detection/pytorch_detector.py).
Les erreurs par image sont conservées dans `detections.json`, distinctement d'une
détection réussie sans animal. Les détections ne sont pas mises en cache entre exécutions.

`TorchClassifier` charge explicitement un checkpoint local avec
`torch.load(..., weights_only=True)`, valide les classes, crée l'architecture
`timm` avec `pretrained=False`, puis charge ses poids. Aucune lecture de poids à
l'import. Le modèle et ses transformations utilisent la taille d'image du checkpoint.

## Utilisation depuis un worker ou un script

Les fonctions métier ne dépendent ni de la CLI ni de Redis :

```python
from pathlib import Path

from biosentinelle_vision.classes import load_classes
from biosentinelle_vision.config import VisionSettings
from biosentinelle_vision.datasets.inventory import inventory
from biosentinelle_vision.datasets.split import split_videos
from biosentinelle_vision.datasets.frames import extract_frames
from biosentinelle_vision.storage import LocalStorage

settings = VisionSettings(dataset_root=Path("data/datasets"))
classes = load_classes(settings.classes_manifest)
videos = split_videos(inventory(settings.dataset_root, classes), settings.split, settings.seed)
frames = extract_frames(videos, LocalStorage(settings.output_root), settings.frames)
```

Autres points d'entrée réutilisables :

- `detection.batch.detect_frames` accepte le protocole `Detector`.
- `datasets.crops.build_crops` construit seulement de vrais crops de détection.
- `datasets.review.apply_review` confirme/corrige/rejette, régénère le crop dans
  `reviewed/` et écrit `review.json` sans modifier le split.
- `training.dataset.select_samples` exclut par défaut les crops non validés et vérifie
  l'absence de groupes partagés entre ensembles.
- `training.engine.train` entraîne explicitement en deux phases, avec sauvegarde
  du meilleur macro-F1 et historique ; les labels sont humains ou explicitement provisoires,
  chaque classe doit être présente en train et une validation doit exister.
- `evaluation.predict.predict_test_crops` produit `predictions.json` sur les
  crops test validés avec un vrai `Classifier`.
- `inference.video.analyze_video` reçoit séparément `Detector`, `Classifier` et
  un `Tracker` neuf ; traite les frames séquentiellement et exporte un MP4 et un rapport.

Les modèles sans checkpoint initial sont initialisés aléatoirement : le transfert
ImageNet automatique du notebook est volontairement supprimé pour éviter le
téléchargement implicite. `train(..., initial_checkpoint=Path(...))` accepte un
checkpoint local compatible. Le batch par défaut est 4, la précision est complète,
et les checkpoints sont dans `checkpoint_root`, séparés des résultats.
Ce n'est pas une garantie de tenir en VRAM pour toutes les architectures.

Les opérations CLI GPU et les fonctions `train`/`analyze_video` utilisent un verrou
interprocessus. Tous les appels doivent partager `gpu_lock_path`. Si un appelant
construit lui-même des modèles CUDA avant ces fonctions, il doit sérialiser aussi
cette construction ; ne pas imbriquer deux acquisitions du verrou. Aucun modèle
n'est construit et aucune tâche n'est consommée automatiquement par le worker Redis
existant. Aucun raccordement HTTP ou interface de revue web n'est ajouté.

## Évaluation

```sh
biosentinelle-vision evaluate --predictions data/results/vision/predictions.json --output data/results/vision/metrics.json
```

Cette commande évalue des **probabilités existantes**, elle ne prétend pas inférer
sans checkpoint. Schéma minimal de `predictions.json` (dix probabilités dans l'ordre) :

```json
{
  "schema_version": "1",
  "class_manifest_version": "v3-10.1",
  "classes": ["chevreuil", "sanglier", "buse", "pigeons", "martres", "renards", "blaireaux", "chouette", "geai", "faisans"],
  "predictions": [{
    "crop_id": "crop-1", "video_id": "video-1",
    "truth": "renards", "human_validated": true,
    "probabilities": [0, 0, 0, 0, 0, 1, 0, 0, 0, 0]
  }],
  "video_truth": {"video-1": "renards"}
}
```

Les labels humains doivent effectivement provenir d'une revue ; le booléen est
une attestation fournie par l'appelant, pas une preuve automatiquement vérifiable.
Sans vérité vidéo humaine unique, la métrique vidéo est omise pour cette vidéo
et son identifiant est signalé. Aucune majorité de crops ne devient une vérité.
Le macro-F1 est calculé sur toutes les dix classes, y compris les classes absentes
dont le support est explicitement affiché. Les pistes IoU restent des estimations,
sans garantie de dénombrer des individus distincts.

L'export annoté ne conserve pas l'audio ; le codec `mp4v` n'est pas garanti lisible
dans tous les navigateurs. Les annotations image montrent le label de cette image ;
la consolidation temporelle figure dans le rapport. Les frames non analysées ne
reçoivent pas de boîtes périmées maintenues artificiellement.

## Configuration

Pour le dataset nommé par espèce, lancer depuis la racine :
`make prepare-training DEVICE=cuda`, puis `make train DEVICE=cuda BATCH_SIZE=2`.
Les poids MegaDetector locaux sont requis avant la préparation (README principal).
`DEVICE=cpu` fonctionne aussi. La CLI de préparation est
`biosentinelle-vision prepare-training --inventory <videos.json>`.

Les recadrages sans revue restent `review=pending` même si `label` reprend
`frame.species_candidate`. La sélection autorise ces labels seulement avec
`training.allow_filename_labels=true` ou `train --allow-filename-labels`.
Make passe explicitement cette option (désactivation : `ALLOW_FILENAME_LABELS=0`).
Les corrections humaines sont prioritaires ; les refus et les candidats inconnus
sont exclus. Les scores de validation et checkpoints indiquent si les labels
sont humains. `evaluate` et `predict_test_crops` gardent leur exigence de vérité
humaine. Aucun score sur noms de fichiers n'est présenté comme vérifié.

`VisionSettings` utilise Pydantic Settings, sans instance globale. Préfixe
`BIOSENTINELLE_VISION_` et séparateur imbriqué `__`, par exemple :

```sh
docker compose run --rm -e BIOSENTINELLE_VISION_FRAMES__MAX_PER_VIDEO=8 vision biosentinelle-vision extract-frames --inventory /storage/results/vision/inventory.json
```

Les champs et valeurs par défaut sont dans `config.py` : racines dataset/résultats/
checkpoints, chemin de verrou GPU, manifeste de classes, poids détecteur et
checkpoint classificateur, `device`, graine, seuils et pas d'inférence ; sections
`frames`, `crops`, `split`, `tracking` et `training`. Les variables doivent être
exportées ou passées au conteneur : la CLI ne lit pas automatiquement le `.env`
Compose. Compose définit les racines `/storage/...` et le mode CPU ; son fichier
GPU impose `device=cuda`. Ces chemins sont indépendants du chemin hôte.

## Tests

```sh
docker compose --profile test run --build --rm tests
docker compose --profile test run --rm tests ruff check backend shared workers tests infra/init_storage.py
docker build --target vision-test-ml -f backend/Dockerfile -t biosentinelle/vision-test-ml:local .
docker run --rm --network none biosentinelle/vision-test-ml:local
```

La suite par défaut fonctionne sans PyTorch ni GPU. Le test ML facultatif est
ignoré si PyTorch/timm sont absents ; sa cible dédiée installe les roues **CPU**
verrouillées et exécute un véritable petit entraînement et rechargement de modèle
sur données synthétiques, sans réseau à l'exécution. Aucun poids entraîné sur
ces fixtures n'est distribué ni présenté comme un modèle biodiversité.
Les tests de contrats utilisent aussi des fixtures détecteur/classificateur
strictement internes aux tests. Les modèles MegaDetector réels et les performances
scientifiques nécessitent des poids et données validés qui ne sont pas fournis ici.

Validation du 22 octobre 2026 : inventaire réel des 343 vidéos (aucune erreur de
lecture), extraction de 24 JPEG et d'un manifeste sur une vidéo locale. Le test
ML CPU effectue réellement les deux phases sur un petit modèle et recharge son
checkpoint, sans réseau. Il ne mesure aucune performance biodiversité.

Vérification de la préparation automatique : 52 tests sans GPU réussis et deux
tests ML CPU réussis (labels humains et provisoires). MegaDetector MDv5a réel,
poids officiels contrôlés par empreinte MD5, a traité deux images de
`Chevreuil-Scene-010.mp4` et produit deux recadrages sans erreur, hors réseau.
Ce test limité est conservé sous `data/results/vision/real-preparation-smoke/` ;
la préparation complète des 343 vidéos et l'entraînement du dataset ne sont
pas exécutés par les tests. L'inférence GPU a depuis été vérifiée avec la vidéo
réelle et le checkpoint local : voir [les résultats de validation](INFERENCE.md#validation-locale).
