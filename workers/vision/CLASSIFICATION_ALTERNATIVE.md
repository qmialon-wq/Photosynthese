# Classification alternative — progression et contrats

Le détecteur reste MegaDetector 10.0.28 / MDv5a.0.0. Le référentiel reste
`manifests/classes-v3-10.json`, avec les dix indices historiques et leurs alias.
SpeciesNet ne figure pas dans le code actif. Les étapes sont livrées séparément.

## Étape 1 : contrats et adaptateurs

`classification.base.SpeciesClassifier` définit le chargement explicite d'une
`ModelVersion`, les prédictions par image et par batch, les probabilités ordonnées,
les noms de classes, les métadonnées et le déchargement. `Classifier`, le protocole
historique batché, reste disponible sans changement de signature.

`ExistingClassifierAdapter` et `SupervisedClassifier` chargent de vrais checkpoints
PyTorch locaux via le chargeur existant. Construire un adaptateur ne charge aucun
poids. `load()` vérifie la famille, le prétraitement et l'empreinte si fournie ; le
chargeur vérifie l'ordre des classes et le state_dict. Aucun téléchargement.

`SpeciesPrediction` contient espèce/indice uniquement si reconnue, scores ordonnés,
confiance, famille, identifiant, version et durée moyenne par crop du batch. Une
erreur n'est jamais transformée en espèce ni en distribution fictive. Le slug reste
le nom canonique du manifeste ; les alias singuliers ne changent pas ses indices.

Le prétraitement `legacy-imagenet-resize-v1` préserve les transformations historiques.
Les profils des nouveaux poids préentraînés seront versionnés séparément.
`LegacyClassifierBridge` restitue les anciennes structures `Prediction` pour le
tracking et le rendu ; une erreur de classification conserve le comportement
d'échec explicite du pipeline. L'intégration au sélecteur de production est une
étape distincte : aucune activation ni double inférence ajoutée ici.

Les tests utilisent des fixtures réservées aux tests et un vrai petit checkpoint
CPU créé explicitement depuis zéro, sans téléchargement. Cet entraînement de test
ne constitue pas un modèle utilisable en production.

## Étape 2 : manifestes de comparaison

`python -m biosentinelle_vision.datasets.benchmark --manifest <training.json>
--inventory <videos.json> --storage-root <results/vision> --output <versions>`
enrichit un manifeste existant (utiliser le snapshot fusionné avec la revue humaine).
Le mode par défaut exige une annotation humaine et exclut les images floues ou trop
petites. `--allow-weak-labels` est une expérience explicite ; les vidéos signalées
multi-espèces restent exclues de ce mode. Les slugs et noms latins viennent du
référentiel. Aucun label ni split n'est écrit dans les sources.

La version est le SHA-256 d'un manifeste canonique contenant hashes d'images,
chemins des vidéos, instants, boîtes, provenance des labels, paramètres, qualité,
doublons et avertissements. `training.json` conserve le format du moteur existant.
Les quasi-doublons inter-splits font échouer la préparation, pour imposer un
regroupement en amont ; aucun déplacement silencieux d'un exemple test.
Les classes rares sont signalées, sans empêcher la production du manifeste.
La fraction de premier plan est une estimation géométrique de la marge déclarée,
pas une segmentation de l'animal. Les boîtes initiales et historiques corrigés
restent dans la revue SQL ; la boîte de ce manifeste est celle effectivement utilisée.

```sh
docker compose --profile test run --rm --no-deps \
  -e PYTHONPATH=/app:/app/backend:/app/workers/vision \
  -v ./workers:/app/workers:ro -v ./tests:/app/tests:ro \
  tests pytest tests/vision/test_species_classifier.py -m 'not gpu and not real_model' -p no:cacheprovider
```
