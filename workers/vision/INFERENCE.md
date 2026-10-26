# Inférence locale

Depuis la racine du dépôt, Docker démarré (le venv hôte n'intervient pas) :

```sh
make detector-fetch
make inference-up DEVICE=cuda
```

`DEVICE=cpu` démarre aussi le consommateur ML sans NVIDIA, plus lentement.
`docker compose up -d` garde un worker léger sans consommation des analyses.
Le checkpoint réel `data/checkpoints/classifier_v3_best.pt` est nécessaire pour
classer ; son absence fait échouer explicitement la tâche, sans modèle de secours.

## Détecteur compatible

Le couple testé est **megadetector==10.0.28 / MDv5a.0.0**. L'adaptateur appelle
`megadetector.detection.run_detector.load_detector(local_path, force_cpu=...,
force_model_download=False)`, puis `generate_detections_one_image`.
La version installée et les signatures sont vérifiées avant chargement.

```sh
make detector-info
make detector-test DEVICE=cuda IMAGE=/storage/results/vision/real-preparation-smoke/frames/REMPLACER_PAR_UNE_IMAGE.jpg
```

Choisir une vraie image extraite, ou copier un JPEG sous `data/datasets/inbox/`
et utiliser `IMAGE=/storage/datasets/inbox/test.jpg`. Le test produit
`data/results/vision/detector-test/annotated.jpg` et `detections.json`.

`detector-fetch` est la seule commande qui télécharge des poids. Elle utilise
le [fichier officiel de la publication v5](https://github.com/agentmorris/MegaDetector/releases/tag/v5.0),
dans `/storage/models/md_v5a.0.0.pt`, monté en écriture. Le cache est contrôlé
par SHA256 et MD5 à chaque utilisation ; le MD5 provient du
[registre officiel](https://github.com/agentmorris/MegaDetector/blob/main/megadetector/detection/run_detector.py),
le SHA256 est calculé sur cet artefact vérifié. Le registre local est versionné
dans `detection/weights.py`. Un téléchargement temporaire n'est publié qu'après
vérification et renommage atomique. Un fichier existant corrompu est refusé,
sans écrasement silencieux. Le manifeste adjacent conserve modèle, URL, version
du package et empreinte. Les imports et le démarrage ne téléchargent rien.

Le service de téléchargement a une sortie réseau ; le worker reste sur le réseau
interne et utilise exclusivement les poids locaux. Aucun appel à SpeciesNet,
Kaggle, Colab ou `ultralytics.YOLO` n'est utilisé pour charger ces poids.

## API asynchrone

Déposer une vidéo complète dans `data/datasets/inbox/`. Sous PowerShell :

```powershell
$body = @{ video='ma-video.mp4'; detection_threshold=0.10; classification_threshold=0.48; track_threshold=0.60; track_min_hits=2; infer_every_n_frames=10 } | ConvertTo-Json
$job = Invoke-RestMethod -Method Post http://localhost:8000/vision/analyses -ContentType 'application/json' -Body $body
Invoke-RestMethod ("http://localhost:8000" + $job.status_url)
```

La soumission répond **202** avec un identifiant et une URL de suivi ; elle
vérifie seulement le chemin et l'existence du fichier, sans décodage, hash ni ML.
Les chemins sont relatifs à inbox, avec `/` ; chemins absolus et traversées refusés.
La file indisponible donne 503. La documentation interactive est `/docs`.

États de tâche : `queued`, `running`, `completed`, `error`. Après succès :

```text
GET /vision/analyses/<id>/artifacts/video
GET /vision/analyses/<id>/artifacts/report
GET /vision/analyses/<id>/artifacts/statistics
```

Redis Streams acquitte après enregistrement du résultat. Un message interrompu
est repris au redémarrage du consommateur unique. Son bail Redis est renouvelé
avec le heartbeat pendant les calculs longs ; le verrou fichier GPU couvre le
chargement, l'analyse et la libération des modèles, y compris les commandes CLI.
Si le GPU est occupé, la tâche reste en attente. Le traitement est au moins une
fois : les sorties sont identifiées par contenu, poids, version du pipeline et
configuration. Les erreurs sont conservées ; soumettre `force=true` pour réessayer.
Les états Redis sont conservés sans expiration automatique. L'AOF `everysec`
peut perdre la dernière seconde lors d'une panne brutale de l'hôte.

Pour détecter sans classificateur, soumettre explicitement `detection_only=true`.
Les résultats restent localisés et marqués non classés ; aucune espèce n'est inventée.

La CLI reste disponible : `make analyze DEVICE=cuda`, `make watch DEVICE=cuda`.
Pour détection seule : ajouter `--detection-only` à `biosentinelle-vision analyze`.

## Résultats et seuils

L'extraction d'inférence décode progressivement les frames en mémoire, sans créer
des milliers de JPEG temporaires. Le pas `infer_every_n_frames` détermine les
frames analysées ; les autres sont copiées sans boîtes périmées. Le traitement
enchaîne détecteur, recadrage avec marge, classificateur, puis tracker interchangeable.
Les boîtes des recadrages trop petits restent dans le résultat et le MP4.

| Paramètre | Fonction |
| --- | --- |
| `detection_threshold` | Score minimum MegaDetector « animal » |
| `classification_threshold` | Probabilité minimum pour nommer une espèce sur un crop |
| `track_threshold` | Confiance minimum de la distribution agrégée de la piste |
| `track_min_hits` | Nombre minimum de prédictions sur la piste |
| `tracking.iou_threshold` | Association géométrique, sans lien avec la confiance d'espèce |

Les votes temporels utilisent toutes les distributions disponibles, y compris
incertaines. Les probabilités sont moyennées sur la piste ; un score agrégé n'est
pas une probabilité calibrée. `max_misses` compte des mises à jour analysées,
pas des frames non échantillonnées. L'identité d'une piste n'est pas une garantie
d'individu distinct. Les métriques de suivi décrivent associations, pistes créées,
confirmées et expirées ; MOTA/IDF1 ne sont pas calculables sans vérité annotée.

Le rapport JSON **schema_version=2** contient les frames analysées, coordonnées
normalisées `x,y,w,h`, score de détection, dix probabilités de classification,
score et label classificateur, identifiant de piste et agrégats temporels.
La provenance du modèle classificateur est conservée si son checkpoint la fournit.

Le MP4 conserve les cadres, labels et scores de la dernière image analysée sur
les images intermédiaires : avec un pas de 10, le même résultat est affiché sur
les 9 images suivantes, sans appel supplémentaire au détecteur, au classificateur
ou au tracker. L'analyse suivante remplace l'ensemble des annotations ; si elle
ne détecte aucun animal, les cadres disparaissent. Le dernier résultat est aussi
conservé jusqu'à la fin d'un bloc incomplet. Il s'agit d'un maintien visuel à
coordonnées fixes, sans interpolation du mouvement. Le JSON et les statistiques
comptabilisent uniquement les véritables analyses (`annotation_display` vaut
`hold_last_analysis`). La version du cache est incrémentée pour les nouveaux
lancements ; les MP4 déjà générés doivent faire l'objet d'une nouvelle analyse.

| État | Signification |
| --- | --- |
| `no_detection` | Aucun animal détecté ; résultat valide, MP4 conservé |
| `detection_unclassified` | Animal localisé, sans prédiction exploitable |
| `species_uncertain` | Prédiction disponible, confiance ou durée de piste insuffisante |
| `species_recognized` | Espèce reconnue au niveau considéré (crop ou piste) |

`report.json`, `statistics.json`, `annotated.mp4`, `state.json` sont sous
`data/results/vision/analyses/<nom>-<empreinte>/`. Le statut global utilise les
pistes confirmées ; les statuts par détection utilisent le seuil de classification.
Les diagnostics indiquent frames décodées/analysées/avec détection, recadrages
valides, prédictions et durées détecteur/classificateur/total. Le temps GPU est une
durée CUDA Events synchronisée des appels d'inférence (avec leurs attentes), hors
chargement des modèles ; sur CPU il vaut `null`. Les MP4 sont encodés en `mp4v`
sans audio ; leur lecture navigateur dépend du codec. Le JSON détaillé et les
résumés temporels occupent une mémoire proportionnelle aux observations analysées.

## Vérifications

```sh
make test
make lint
make detector-fetch
make inference-test DEVICE=cuda REAL_VIDEO=/storage/datasets/inbox/test.mp4 INFER_STRIDE=30
```

Le dernier test est facultatif (`pytest -m real_model`) : vraie vidéo, vrais poids
et vrai checkpoint, sans modèle simulé. Il produit un MP4, un rapport, des stats
et `detector-image.jpg` dans `data/results/vision/integration/`. Il vérifie le
fonctionnement et la structure, sans attester la qualité écologique des prédictions.
Les tests unitaires sans GPU utilisent uniquement des fixtures internes aux tests.

## Validation locale

Le 22 octobre 2026, le démarrage Compose ML GPU a réussi avec les services sains.
Une soumission HTTP a traité `diagnostic-chevreuil.mp4` (copie d'une vidéo locale) :
971 frames décodées, 33 analysées, 33 détections, 33 recadrages valides et
33 prédictions, une piste chevreuil. Les scores de la première observation sont
distincts : détecteur 0,936 ; classificateur environ 0,941. Le rapport JSON, les
statistiques et le MP4 ont été récupérés depuis l'API ; la vidéo répond aussi
206 aux requêtes Range. Temps CUDA de cet appel : environ 7,2 s hors chargement.

`make inference-test DEVICE=cuda REAL_VIDEO=/storage/datasets/inbox/diagnostic-chevreuil.mp4 INFER_STRIDE=30`
a réussi avec MDv5a réel, le classificateur local et la RTX 3050 Ti. L'image
`data/results/vision/integration/detector-image.jpg` a été inspectée : la boîte
localise le chevreuil. Ce contrôle fonctionnel d'une vidéo n'est pas une mesure
de précision sur un jeu de test indépendant.
