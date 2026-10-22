# Correspondance du notebook V3

Référence lue intégralement : `BioSentinelle_V3_Colab_Complet.ipynb`, 27 cellules,
indices ci-dessous à partir de zéro. Le notebook n'est ni modifié ni exécuté.
Empreinte SHA-256 : `f28f99b30acb555212dca4e47b310b41860bfb6c33a2406ff2d9a1c5f3a7a0cc`.

| Cellule | Contenu / fonctions historiques | Module réutilisable |
| --- | --- | --- |
| 0 | Introduction, limites scientifiques | Ce document et README du package |
| 1 | Montage Drive | Supprimé ; `storage/local.py` |
| 2 | Installation interactive des dépendances | `requirements.in`, verrou et extras ML explicites |
| 3 | Imports, constantes, classes, chemins et graines | `config.py`, `classes.py`, `manifests/classes-v3-10.json` |
| 4 | Consignes inventaire/split | `datasets/inventory.py`, `datasets/split.py` |
| 5 | `species_from_path`, `split_species` | `species_candidates`, `inventory`, `split_videos` |
| 6 | Consignes extraction | `datasets/frames.py` |
| 7 | Boucle extraction, cache JPEG/index | `extract_frames` et manifeste JSON typé |
| 8 | Contrat MegaDetector | `detection/base.py`, `detection/megadetector.py` |
| 9 | `detect_image`, `draw_detections` | `MegaDetector.detect`, `inference/render.py` |
| 10 | Détection complète et cache | `detection/batch.py` ; erreurs distinctes de zéro détection |
| 11 | Qualité des crops | `datasets/crops.py` |
| 12 | `crop_xywh`, boucle crops | `crop_image`, `build_crops` |
| 13 | Consignes revue humaine | `datasets/review.py` |
| 14 | `persist_review`, `refresh`, `action`, widgets | `apply_review` ; widgets non portés, pas d'interface web ajoutée |
| 15 | Consignes manifeste final | `training/dataset.py` |
| 16 | Revue, filtrage et quotas par vidéo | `select_samples` ; validation humaine requise |
| 17 | Consignes entraînement | `training/engine.py` |
| 18 | Transformations, `CropsDS`, loaders, création modèle | `classification/preprocessing.py`, `training/dataset.py`, `classification/model.py` |
| 19 | `freeze_backbone`, `unfreeze_all`, `evaluate`, `train_phase` | `training/engine.py` ; fonctions sans variables globales |
| 20 | Consignes évaluation | `evaluation/metrics.py` |
| 21 | `probabilities`, métriques crop/vidéo | `TorchClassifier.predict`, `evaluate_predictions` |
| 22 | Consignes vidéo libre | `inference/video.py` |
| 23 | Upload Colab | Remplacé par un `Path` local passé à `analyze_video` |
| 24 | Extraction, `iou`, association et votes | `inference/video.py`, `tracking/iou.py` |
| 25 | Consolidation, export MP4 et JSON | `inference/render.py`, rapport de `analyze_video` |
| 26 | Diagnostic et limites | README ; erreurs explicites, compte de pistes estimé |

## Divergences décidées

1. **Classes** : malgré les mentions « 11 », le code contient dix classes. Après
   confirmation utilisateur du 22 octobre 2026, conserver exactement ces dix
   identifiants et indices. Le merle n'est pas ajouté. Les alias de fichiers
   n'altèrent jamais les identifiants de sortie.
2. **Imports** : aucune création de dossier, graine globale, détection CUDA,
   installation, lecture de dataset ou construction de modèle lors des imports.
3. **Poids** : MegaDetector reçoit un fichier local existant, jamais un nom de
   modèle téléchargeable. Les classificateurs sont créés avec `pretrained=False`.
   Les checkpoints sont chargés avec `weights_only=True`, ordre des classes
   contrôlé. Aucun remplissage ni permutation silencieuse des sorties.
4. **Labels** : le nom de fichier ne donne qu'un candidat. Les cas inconnus ou
   ambigus sont conservés dans l'inventaire. Les parents hors dataset ne sont
   pas consultés. L'entraînement accepte explicitement les labels provisoires
   (`training.allow_filename_labels=true`), sans les transformer en labels humains.
   Les scores de validation portent cette provenance dans l'historique et le
   checkpoint ; la commande d'évaluation exige toujours des labels humains.
5. **Split** : séparation déterministe par groupe vidéo avant extraction ; copies
   identiques regroupées par empreinte du contenu. Une séquence étendue peut être
   fournie explicitement comme groupe ; sa déduction depuis un nom est insuffisante.
6. **Extraction** : pas de faux FPS à 25. Métadonnées invalides, lectures et écritures
   ratées sont rapportées. Espacement minimal calculé sur les indices réels. Pas
   de réutilisation aveugle de JPEG/cache ; manifests remplacés atomiquement.
7. **Détection** : une panne n'est jamais enregistrée comme une liste vide réussie.
   Pas de cache ML réutilisé sans identité des poids et paramètres ; cette version
   recalcule explicitement. Aucun détecteur de remplacement.
8. **Revue** : état métier indépendant des widgets. Une nouvelle boîte acceptée
   régénère réellement le crop, sans modifier le split ; les rejets sont exclus.
9. **Évaluation** : aucune vérité vidéo déduite de la classe majoritaire des crops.
   Les métriques vidéo nécessitent une vérité vidéo humaine explicite ; les vidéos
   multi-espèces sans vérité unique sont omises et signalées. Confusion dynamique.
10. **Training** : batch initial réduit pour la VRAM, précision complète par défaut
    (pas d'autocast float16 sans GradScaler), pertes pondérées par nombre d'exemples,
    meilleur checkpoint rechargé avant finetuning. Les opérations sont explicites.
11. **Tracking** : association un à un, expiration explicite des pistes, votes
    temporels séparés des prédictions image. Une piste n'est pas un individu unique.
12. **Inférence** : crops en mémoire, pas de `_infer_crop.jpg` partagé. Traitement
    vidéo séquentiel ; les boîtes ne sont pas maintenues artificiellement sur les
    frames non analysées. Export sans audio, codec OpenCV `mp4v`, non garanti web.

Les adaptateurs ML réels nécessitent des dépendances optionnelles et des poids
locaux. Les fixtures de tests ne sont jamais utilisées comme modèles en production.
