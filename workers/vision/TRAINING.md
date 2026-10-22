# Entraînement local

Le manifeste reste celui des **10 classes confirmées**, version `v3-10.1`, dans
l'ordre historique. Aucun indice supplémentaire n'est inventé.

## Classificateur sur recadrages

Depuis la racine, avec Docker démarré :

```sh
make training-up DEVICE=cuda
make train-classifier BATCH_SIZE=2 ACCUMULATION_STEPS=4
```

Le premier appel démarre le worker ML, PostgreSQL et Redis ; il ne crée aucune
tâche d'entraînement. Le second soumet explicitement un job au même Redis Stream
que l'inférence. Le client de soumission n'exige pas de GPU ; le **worker déployé**
choisit CPU ou CUDA. Un seul consommateur exécute les tâches lourdes et le verrou
GPU protège aussi les appels Python. Aucune opération longue ne passe par HTTP.

Le dataset par défaut est `data/results/vision/review.json`, avec des recadrages
acceptés et étiquetés humainement dans chaque classe en train, et un val non vide.
La CLI `train-classifier` ignore le mode provisoire hérité de Make, sauf demande
explicite `--allow-filename-labels` ou configuration JSON correspondante. Le parcours
historique `make train` garde son mode provisoire explicite ; ses scores sont marqués.
Les noms des vidéos ne constituent jamais une validation de chaque animal.

Configurations fournies :

```sh
make train-classifier TRAIN_CONFIG=/app/workers/vision/configs/classifier-efficientnetv2.json
```

Le défaut est `classifier-rtx3050.json` : `convnext_tiny`, images 224, micro-batch 2,
accumulation 4 (batch effectif nominal 8), zéro sous-processus de chargement.
EfficientNetV2 utilise `tf_efficientnetv2_b0` ; `efficientnetv2_s` et
`efficientnetv2_rw_t` sont également disponibles. Le vrai backbone timm
`mobilenetv3_small_050` permet les tests CPU rapides. Les architectures sont créées
avec `pretrained=False`, sans téléchargement. Un checkpoint initial local
compatible peut être fourni ; l'entraînement depuis zéro ne garantit pas une
bonne précision avec un petit dataset.

La configuration JSON décrit `VisionSettings` (sections `training`, racines, seed).
Dans Make, `BATCH_SIZE`, `ACCUMULATION_STEPS`, `IMAGE_SIZE`, `EPOCHS_HEAD` et
`EPOCHS_FINETUNE` priment sur le JSON pour un nouveau run.
Les options CLI explicites priment sur la configuration. Les configurations fournies
contiennent des chemins de conteneur `/storage/...`. Pour un autre manifeste, modifier
le JSON ou utiliser directement `--manifest`.

Exemples CLI dans le conteneur vision :

```sh
biosentinelle-vision train-classifier --config /app/workers/vision/configs/classifier-rtx3050.json --manifest /storage/results/vision/review.json --model convnext_tiny --batch-size 2 --accumulation-steps 4
biosentinelle-vision train-classifier --resume /storage/checkpoints/<run_id>/last.pt
```

La réponse contient l'ID du job et son `status_url` (`GET /vision/analyses/<job_id>`).
Arrêter le client après soumission n'annule pas le job. `SIGTERM` du worker demande
un arrêt ; le job non acquitté est repris au prochain démarrage. Il n'y a pas encore
de commande d'annulation individuelle pendant qu'un worker reste actif.

## Second modèle EfficientNetV2 pour le POC

Ce parcours crée un modèle indépendant de SpeciesNet et du ConvNeXt,
initialisé aléatoirement, sans téléchargement. Depuis la racine :

```sh
make training-up DEVICE=cuda
make efficientnet-poc-check DEVICE=cuda
make train-efficientnet-poc DEVICE=cuda
```

Configuration : `configs/classifier-efficientnetv2-poc.json`, B0, 224 px,
batch 2, accumulation 4, AMP, deux époques de tête puis jusqu'à 30 époques sur
l'ensemble du CNN, early stopping après huit époques sans progrès. Les taux
d'apprentissage sont adaptés à cette initialisation depuis zéro.

Le contrôle construit un snapshot sous `data/results/vision/poc/efficientnetv2-v1/`.
Les recadrages provisoires viennent de `training.json`, avec l'autorisation explicite
des labels de noms. Pour les vidéos reconnues par SHA-256 dans la revue SQL, tous
les anciens recadrages sont remplacés par les validations/corrections actuelles ;
les rejets et exemples à revoir sont exclus. Les boîtes corrigées utilisent leur
dernier rendu. Les splits de l'inventaire initial sont conservés, même si une vidéo
de test a été importée séparément en train dans la revue. Un groupe test gelé reste
test ; les copies de contenu présentes dans plusieurs splits sont refusées.
Les vidéos de revue sans correspondance SHA ne sont pas ajoutées automatiquement,
afin de ne pas introduire un extrait lié à une autre vidéo dans un autre ensemble.
Le snapshot existant n'est pas remplacé : pour intégrer de nouvelles corrections,
créer une configuration avec un nouvel identifiant et une nouvelle destination.

La soumission passe par Redis et le consommateur GPU unique. Le run
`efficientnetv2-poc-v1` et ses métriques sont visibles dans **Administration →
Entraînements → Runs et checkpoints existants**. Checkpoints persistants :
`data/checkpoints/efficientnetv2-poc-v1/{best,last}.pt`. En cas d'interruption, le
worker reprend `last.pt` à la dernière frontière d'époque enregistrée.

Après réussite, le worker vérifie et enregistre `best.pt`, puis active cette version
pour les prochaines analyses web. Le ConvNeXt reste enregistré et son fichier est
conservé : revenir dessus dans **Modèles → Activer**. Les analyses CLI historiques
utilisent toujours leur `CLASSIFIER_CHECKPOINT` explicite. Le registre conserve la
provenance provisoire ; les métriques ne constituent pas une évaluation humaine
fiable. L'activation signifie que le modèle est utilisable, pas qu'il a démontré
une meilleure qualité que le précédent. Aucun entraînement au démarrage.

Les options génériques `training.register_model_name` et
`training.activate_on_success` sont désactivées par défaut. L'activation requiert un
nom d'enregistrement, un entraînement terminé et un chargement strict du checkpoint
réussi. Ces options ne modifient pas l'empreinte de reprise des anciens runs.

Reprise explicite via la file, uniquement si le run n'est plus en cours :

```sh
make train-classifier DEVICE=cuda RESUME=/storage/checkpoints/efficientnetv2-poc-v1/last.pt
```

## Phases, mémoire et reproductibilité

La première phase entraîne la tête avec le backbone figé ; la seconde recharge
le meilleur état puis affine l'ensemble. AdamW, décroissance cosinus, label
smoothing, arrêt anticipé par macro-F1 image et équilibrage pondéré modéré
(exposant 0,5, ratio plafonné à 3) sont configurables. Les augmentations appliquent
recadrage modéré, miroir horizontal, variations limitées de couleur et flou léger,
sans retournement vertical ni rotation irréaliste.

AMP `auto` utilise bfloat16 CUDA lorsqu'il est disponible, sinon float16 avec
GradScaler. `off` reste disponible ; les modes explicites incompatibles sont refusés.
Sur CPU, `auto` garde float32. L'accumulation normalise par le nombre réel d'images,
y compris le dernier groupe incomplet. Les statistiques BatchNorm sont figées
si le micro-batch tombe à 1.

Une OOM fait revenir au checkpoint du début d'époque, avec restauration du modèle,
optimiseur, scheduler, scaler et RNG. Le micro-batch est divisé par deux et
l'accumulation ajustée pour conserver au moins le batch effectif demandé. Trois
essais sont autorisés par phase par défaut. Une OOM persistante à batch 1 échoue
explicitement ; les checkpoints restent disponibles. Une taille d'image différente
exige un nouveau run, car elle change l'expérience.

Les splits doivent être établis **par vidéo avant extraction**. Le moteur refuse
une vidéo, un groupe ou une clé d'image présents dans plusieurs ensembles. Il ne
refait jamais un split par image. Les séquences liées doivent partager un groupe
correct ; leur indépendance ne peut pas être garantie seulement par leurs noms.

Chaque run conserve configuration, ordre des classes, manifeste sélectionné,
hash des images et vérité vidéo, versions Python/PyTorch/timm, seed et RNG.
Les algorithmes déterministes sont activés par défaut. Une reprise vérifie
l'empreinte des données et des hyperparamètres. La reproductibilité exacte est
visée dans le même environnement ; changer matériel ou versions peut changer
les résultats, comme le précise la [documentation PyTorch](https://docs.pytorch.org/docs/2.6/notes/randomness.html).

## Persistance et reprise

```text
data/checkpoints/<run_id>/best.pt          poids du meilleur macro-F1, pour inférence
data/checkpoints/<run_id>/last.pt          état complet, pour reprise
data/checkpoints/<run_id>/config.json      configuration lisible de reprise
data/results/vision/training/<run_id>/run.json
data/results/vision/training/<run_id>/history.json
data/results/vision/training/<run_id>/manifest.json
data/results/vision/training/<run_id>/database_sync.json
```

Les écritures de checkpoint sont atomiques. `last.pt` comprend modèle, meilleur
modèle, optimiseur, scheduler, scaler, RNG, phase, époque, early stopping, historique
et tailles de batch. **La reprise se fait à la dernière frontière d'époque** :
une époque interrompue est rejouée, pas toutes les époques précédentes. Une interruption
très précoce, avant création de `last.pt`, recommence la première époque.

```sh
make train-classifier RESUME=/storage/checkpoints/<run_id>/last.pt
```

La reprise récupère sa configuration et ignore les valeurs Make par défaut de
batch ou de backbone ; elle refuse des changements incompatibles. Le worker
reprend aussi automatiquement `last.pt` lorsqu'un job déjà soumis est interrompu.
Les volumes persistent après redémarrage/recréation Docker. Aucun run ne remplace
le checkpoint de production historique `classifier_v3_best.pt` : pour analyser
avec le nouveau modèle, sélectionner explicitement
`CHECKPOINT=/storage/checkpoints/<run_id>/best.pt`.

## Évaluation et métriques

```sh
make evaluate-classifier DEVICE=cuda CHECKPOINT=/storage/checkpoints/<run_id>/best.pt
```

La CLI `evaluate-classifier --checkpoint ... --manifest ... --split test` évalue
strictement des recadrages validés humainement. Sur GPU, elle soumet aussi une
tâche Redis ; sur CPU elle s'exécute directement. Le JSON est écrit dans
`data/results/vision/classifier_evaluation.json` (ou sous la racine configurée).

Les rapports contiennent matrice de confusion, accuracy, précision/rappel/F1
par classe, macro-F1 et classes absentes, par image et par vidéo. Le choix du
meilleur checkpoint utilise uniquement le val, jamais le test. Le moteur n'évalue
pas automatiquement le test à chaque époque.

**Les métriques vidéo exigent une vérité vidéo humaine explicite**, fichier indiqué
par `training.video_truth_manifest` ou `--video-truth`, avec des IDs de vidéo du manifeste :

```json
{
  "class_manifest_version": "v3-10.1",
  "human_validated": true,
  "video_truth": {"id-video-verifiee": "chevreuil"}
}
```

La prédiction vidéo moyenne les probabilités des crops. Sans vérité vidéo unique
vérifiée, la vidéo est omise et signalée ; une majorité de crops ou un nom de fichier
ne devient pas une vérité de référence. Les matrices restent présentes mais leur
support peut être nul. Les métriques d'entraînement sur labels provisoires sont
clairement marquées `human_validated=false`.

Les jobs entraînement enregistrent les métriques dans PostgreSQL par défaut :

```text
GET /training/runs
GET /training/runs/<run_id>
GET /training/runs/<run_id>/metrics
```

La migration Alembic `0002_training_metrics` crée les deux tables. Le couple
`run_id,event_key` évite les doublons après reprise. Les JSON et checkpoints
restent la source de vérité en cas d'indisponibilité PostgreSQL ; `database_sync.json`
signale `pending`. Rejouer explicitement la projection après rétablissement :

```sh
biosentinelle-vision metrics-sync /storage/results/vision/training/<run_id>
```

Les temps et pics mémoire des tests synthétiques ne représentent pas le temps
d'entraînement de toutes les vidéos. La file Redis fournit un traitement au moins
une fois ; un checkpoint d'époque limite le travail rejoué après panne.

## Détecteur : interface distincte, exécution bloquée sans adaptateur validé

`training/detector.py` expose `DetectorTrainingConfig`, `DetectorTrainer` et une
validation de dataset. Le format canonique `normalized_boxes_v1` contient
`target=animal`, puis pour chaque image : clé locale, SHA256, vidéo, split,
`human_verified=true` et boîtes normalisées `x,y,w,h`. Une image vérifiée sans animal
peut avoir zéro boîte ; le train doit contenir au moins une boîte, et val doit exister.
Les coordonnées, fichiers, empreintes, doublons et fuites de vidéo sont contrôlés.
L'attestation humaine doit correspondre à une vraie revue des annotations.

```sh
biosentinelle-vision detector-train-check --config /storage/results/vision/detector-training.json
```

Ce contrôle ne déclenche aucun entraînement. Aucun adaptateur de fine-tuning du
détecteur n'est fourni à cette étape : `train_detector` refuse explicitement
l'exécution, même avec un dataset valide. Intégrer un moteur demande de vérifier
le format, les catégories et l'architecture des poids. Les crops classifiés ne
suffisent pas et les poids MegaDetector v5 ne sont pas chargés arbitrairement par
`ultralytics.YOLO`.

## Tests sans entraînement de production

```sh
make test
make training-tests DEVICE=cpu
make training-gpu-test DEVICE=cuda
```

La suite CPU vérifie un véritable petit modèle timm, la CLI, les métriques vidéo,
l'accumulation incomplète, une OOM injectée et l'égalité exacte après reprise.
Le test GPU facultatif soumet deux petits jobs synthétiques par Redis avec les
backbones ConvNeXt-Tiny et EfficientNetV2, vérifie AMP, checkpoints et PostgreSQL.
Ses artefacts sont dans `gpu-training-test/` et ne sont jamais promus comme modèles
de biodiversité. `--local` de `train-classifier` est réservé aux tests CPU hors file.

## Validation locale du 22 octobre 2026

Les six tests ML passent dans l'image Docker CPU (PyTorch CPU, Python 3.12),
dont la reprise exacte, l'OOM injectée, la CLI et les métriques vidéo. La suite
sans GPU compte 75 tests réussis, avec six tests ML ignorés sans PyTorch.

Deux jobs GPU synthétiques ont réussi via Redis sur la RTX 3050 Ti : ConvNeXt-Tiny
et EfficientNetV2-B0, 224 pixels, batch 2, accumulation 4, une époque de tête et
une époque de fine-tuning. AMP utilise bfloat16. Pics de mémoire **allouée** mesurés :
environ 0,59 Gio et 0,20 Gio (hors contexte CUDA et autres applications).
Les JSON, checkpoints et métriques PostgreSQL ont été vérifiés.

Après recréation Docker, `last.pt` et son optimiseur restent lisibles ; une reprise
par Redis conserve les deux époques déjà terminées. Une évaluation GPU via Redis
a ensuite traité dix crops test et dix vidéos synthétiques à vérité explicite.
Le checkpoint de production historique n'a pas été remplacé. Ces résultats ne
mesurent pas la précision sur la faune réelle.
