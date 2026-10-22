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

## Étape 3 : entraînement supervisé préentraîné

Les nouveaux entraînements exigent désormais des poids généralistes locaux.
Le téléchargement se fait explicitement avec le module `classification.pretrained` :
`python -m biosentinelle_vision.classification.pretrained tf_efficientnetv2_b0
--root /storage/models/pretrained`. Cette commande nécessite l'accès réseau, pas
les entraînements. Seuls les dépôts officiels référencés par timm sont utilisés ;
révision Git et empreinte SHA-256 LFS sont figées et vérifiées. Un cache existant
est vérifié sans réseau. Formats safetensors uniquement pour ces poids téléchargés.
Voir l'API [timm](https://huggingface.co/docs/timm/main/reference/models) et les
[métadonnées du Hub](https://huggingface.co/docs/huggingface_hub/main/package_reference/hf_api).

Les profils de normalisation/interpolation sont enregistrés dans les checkpoints
et relus à l'inférence. La phase tête gèle le backbone, puis le dégel progresse
par blocs, avec learning rates distincts tête/backbone. Les statistiques des blocs
gelés restent figées. AdamW, scheduler cosine/constant, AMP, accumulation, early
stopping, sauvegarde et reprise sont conservés. Les métriques incluent désormais
macro-précision et macro-rappel. ResNet50 est ajouté et l'alias EfficientNetV2-S
est relié à l'architecture timm réellement disponible `tf_efficientnetv2_s`.

`--initialization scratch` autorise explicitement une expérience depuis zéro.
Les anciens checkpoints sont repris en mode `legacy`, avec le même groupement
d'optimiseur et la même empreinte historique. Changer les données impose un
nouveau run avec `--initial-checkpoint`, pas une reprise prétendue identique.
Une classe absente du train est signalée dans les métadonnées ; les dix sorties
restent présentes. Train et validation doivent rester non vides.

## Étape 4 : embeddings et modèles classiques

L'extracteur alternatif est EfficientNetV2 B0 ImageNet gelé, plus léger que DINOv2
pour ce poste et déjà compatible avec le runtime vérifié. Aucun fine-tuning de
l'extracteur lors de l'extraction. Les vecteurs float32 sont mis en cache par hash
d'image + hash des poids + profil de prétraitement. Les caches sont indépendants
des labels et réutilisables après correction d'une annotation.

La CLI asynchrone est `python -m biosentinelle_vision.classification.cli` :
`extract-embeddings --manifest-key <clé/training.json>` et
`train-embeddings --index-key embeddings/datasets/<version>.json --output-key <run>`.
Les clés d'entrée sont relatives à results/vision ; les modèles à checkpoints.
Ces commandes passent par l'outbox et le consommateur unique existants.

La recherche bornée utilise train pour les transformations, validation pour la
sélection macro-F1, jamais test. k-NN emploie une normalisation L2 ; logistique et
SVM ont un StandardScaler dans leur pipeline. Les SVM sont calibrés par sigmoid
avec des plis StratifiedGroupKFold calculés uniquement sur train ; une classe
insuffisante dans ces plis fait ignorer ce candidat, sans calibration fictive.
RBF est optionnel et limité à 5000 exemples. Les probabilités k-NN sont des votes
pondérés, pas des distances converties arbitrairement ni une calibration garantie.

`EmbeddingClassifier` implémente le même contrat et remet les scores dans les dix
indices canoniques, y compris les classes absentes du train. Les fichiers joblib
sont exclusivement des artefacts locaux produits par l'application ; leur intégrité
et celle de l'extracteur sont contrôlées avant chargement. Ne pas charger de fichiers
joblib externes non fiables. Le registre pourra les identifier par famille.

## Étape 5 : exploration

`cluster-embeddings --index-key embeddings/datasets/<version>.json
--output-key exploration/<run>.json --clusters 10` soumet un K-Means exploratoire.
`--method hdbscan` utilise l'implémentation scikit-learn déjà installée, sans
nouvelle dépendance. PCA et clustering sont ajustés uniquement sur train ; le test
est exclu de l'export. K-Means assigne aussi les exemples de validation ; HDBSCAN
laisse ces exemples non assignés plutôt que simuler une prédiction hors-échantillon.
L'export contient coordonnées, cluster, espèce annotée, provenance, score d'anomalie
et exemples à revoir. Aucun label n'est modifié et aucun classificateur de production
n'est enregistré à partir des clusters.

## Étape 6 : comparaison contrôlée

`evaluation.comparison.compare_classifiers` utilise le même manifeste, les mêmes
hashes de crops, les mêmes classes, seuils et règles d'agrégation pour tous les
modèles. Validation par défaut ; le test n'est jamais utilisé pour sélectionner
un candidat. Les labels faibles exigent une option explicite et rendent le rapport
inapte à une promotion automatique.

Le rapport sépare classification intrinsèque par argmax, fonctionnement au seuil
(abstentions incluses), couverture, erreurs, métriques par espèce, matrices,
latence moyenne batchée, chargement, pic mémoire CUDA et taille des artefacts.
Les échecs restent dans les dénominateurs ; ils ne gonflent pas artificiellement
les scores. Les mesures vidéo utilisent uniquement une vérité vidéo humaine
explicite, sinon elles restent absentes. Le rapport précise que ce benchmark de
crops ne constitue pas une mesure end-to-end de MegaDetector.

## Étape 7 : registre et promotion

La migration `0005_classifier_registry` conserve le champion actif et ajoute famille,
version, dataset, prétraitement, états candidat/validé/actif/archivé, comparaisons
signées par SHA-256 et historique des décisions. Un nouvel entraînement produit
un candidat. L'ancien `activate_on_success` n'active plus directement un modèle.

La politique `BIOSENTINELLE_PROMOTION_*` exige par défaut un gain macro-F1 >0,01,
une baisse de rappel par espèce <=0,05, une baisse de couverture <=0,02 et une
latence <=1,5 fois celle du champion, sans hausse des échecs. Au moins 200 crops
et trois vidéos par classe sont nécessaires, avec un bootstrap groupé par vidéo
(500 tirages, seed fixe, borne basse 95 % du gain positive). Labels faibles et test
ne peuvent jamais servir à promouvoir un modèle. Si les garde-fous passent mais
l'échantillon ne permet pas de conclure, une justification humaine explicite est
requise ; elle ne contourne pas un gain insuffisant ou une régression.

La promotion vérifie aussi champion courant, mapping et empreintes évaluées. Le
rollback restaure un ancien champion, avec acteur et justification enregistrés.
L'ancienne route d'activation refuse désormais un candidat non comparé. Le champion
observé à la migration est conservé, sans prétendre que ses labels historiques sont
validés humainement. Les anciens checkpoints ne sont pas supprimés.

```sh
docker compose --profile test run --rm --no-deps \
  -e PYTHONPATH=/app:/app/backend:/app/workers/vision \
  -v ./workers:/app/workers:ro -v ./tests:/app/tests:ro \
  tests pytest tests/vision/test_species_classifier.py -m 'not gpu and not real_model' -p no:cacheprovider
```
