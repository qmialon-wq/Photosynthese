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

```sh
docker compose --profile test run --rm --no-deps \
  -e PYTHONPATH=/app:/app/backend:/app/workers/vision \
  -v ./workers:/app/workers:ro -v ./tests:/app/tests:ro \
  tests pytest tests/vision/test_species_classifier.py -m 'not gpu and not real_model' -p no:cacheprovider
```
