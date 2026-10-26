# BioSentinelle Normandie

Le [parcours vidéo → parcelle → dossier biodiversité](docs/PARCEL_DOSSIERS.md)
permet de sélectionner plusieurs vidéos d'une même parcelle, de renseigner une seule
fois surface, terrain et projet, puis de retrouver les vidéos annotées et un dossier
textuel commun dans **Mes dossiers**. Les recommandations restent
conditionnelles lorsque les espèces ne sont pas confirmées ; aucun pourcentage de
terrain vert n'est inventé.

Le [module RAG local](docs/RAG.md) propose une recherche documentaire hybride et
des dossiers territoriaux de quatre pages rédigés par un modèle local. Les dossiers
examinent tous les textes extractibles associés aux espèces, puis proposent des
aménagements adaptés au formulaire, avec références, conditions et suivi.
Les documents en attente de validation restent identifiés dans l'audit.
La recherche de passages validés reste disponible avec `make rag-up`,
`make rag-prepare`, puis `make rag-index` ; voir le guide pour préparer Ollama.

Le moteur de classification alternatif (CNN préentraîné local, embeddings et
classifieurs classiques, comparaisons, promotion et rollback) est documenté dans
[CLASSIFICATION_ALTERNATIVE.md](workers/vision/CLASSIFICATION_ALTERNATIVE.md).
Les dix classes et le champion existant sont conservés ; aucun entraînement ni
remplacement de modèle n'est déclenché au démarrage.

Campagne complète des quatre CNN puis benchmark commun, sur le corpus de base
avec labels de noms explicitement autorisés pour le POC :
`make train-benchmark DEVICE=cuda BENCHMARK_WEAK_LABELS=1` (ou `DEVICE=cpu`).
Suivi dans Administration → Entraînements ; comparaison dans Évaluation → Benchmarks.

Socle local Docker : FastAPI, Vue 3 + TypeScript + Vite, PostgreSQL 16 avec
pgvector 0.8.1, Redis et deux workers Python indépendants. Les modules vision
extraits du notebook V3 sont utilisables explicitement depuis Python ou la CLI :
voir le [guide vision](workers/vision/README.md) et la
[correspondance des cellules](workers/vision/NOTEBOOK_MIGRATION.md).
Aucun poids ni modèle entraîné n'est distribué dans Git. Le mode ML active
l'analyse vidéo asynchrone, sans chargement de modèle avant une tâche.
La [veille et l'ingestion scientifiques](workers/documents/README.md) utilisent
OpenAlex, Crossref et Europe PMC dans un worker documentaire indépendant.
La synthèse territoriale locale est décrite dans [le guide RAG](docs/RAG.md).

```sh
make documents-up
make documents-search ARGS='--species "Vulpes vulpes" --focus human_activities --activity transport --limit 5'
```

Les collectes globales ou ciblées, imports, traductions locales en français et retraits multiples sont disponibles
directement dans [Documents scientifiques](http://localhost:8080/documents).

La commande renvoie une tâche asynchrone consultable dans `/documents/tasks/{id}`
et dans la documentation API http://localhost:8000/docs. Le téléchargement de texte
intégral est optionnel (`--download-fulltext`) et limité aux copies explicitement autorisées.

Pour la validation humaine des recadrages, l'historique des corrections et les
exports reproductibles, consulter [HUMAN_REVIEW.md](HUMAN_REVIEW.md).

L'interface web sépare l'espace observation (import, analyse et validation)
de l'administration (datasets, entraînements, modèles et évaluation). Ses parcours sont décrits dans
[WEB_CONSOLE.md](WEB_CONSOLE.md).

L'[inférence vidéo et son API](workers/vision/INFERENCE.md) incluent le
téléchargement explicite vérifié de MegaDetector, le diagnostic de son API,
un test image avec boîtes et une intégration facultative avec modèles réels.

```sh
make detector-fetch
make inference-up DEVICE=cuda
```

Déposer les vidéos dans `data/datasets/inbox/`, puis soumettre
`POST /vision/analyses` (exemples PowerShell dans le guide). Les tâches passent
par Redis ; les MP4, rapports et statistiques sont récupérables depuis l'API.
Le démarrage CPU du socle reste `docker compose up -d`, sans modèles requis.

Le [guide d'entraînement local](workers/vision/TRAINING.md) décrit les phases
ConvNeXt/EfficientNetV2, AMP, reprise, métriques PostgreSQL et garde-fous du
fine-tuning du détecteur. Le manifeste conserve les **10 classes confirmées**.

```sh
make training-up DEVICE=cuda
make train-classifier BATCH_SIZE=2 ACCUMULATION_STEPS=4
```

## Classer les vidéos du dépôt

```sh
make classify-videos
```

Cette commande copie les vidéos de `video datathon/` dans
`data/datasets/classified/<espèce>/`, sans déplacer les originaux. Les fichiers
déjà identiques sont conservés et les destinations différentes ne sont pas écrasées.
Les noms inconnus, ambigus ou les vidéos illisibles sont rangés dans `_a_verifier/`.
Pour changer le dossier source, définir `SOURCE_VIDEOS` dans `.env`.

L'inventaire et le tableau CSV se trouvent dans
`data/results/vision/classification/` (`videos.json`, `classement.csv`,
`classification.json`). Les espèces sont des **candidats déduits des noms de fichiers**.
Le classement ne crée pas de `review.json` et ne valide pas les labels de chaque
animal visible. Les séparations proposées regroupent les copies identiques ;
les scènes issues d'une même prise restent à identifier avant une évaluation fiable.

## Entraînement et vidéos annotées avec Make

Depuis la racine du projet, utiliser GNU Make (sous Windows, WSL est recommandé).
Docker doit être démarré ; le venv Python de l'hôte n'a pas d'effet sur ces commandes.

```sh
make prepare-training DEVICE=cuda
make train-check
make train DEVICE=cuda BATCH_SIZE=2
```

`DEVICE=cpu` est la valeur par défaut, utilisable sans NVIDIA. `DEVICE=cuda`
convient à la RTX 3050 avec Docker/NVIDIA configuré. `ml-build` installe les
bibliothèques ML dans une image facultative ; aucun poids n'est téléchargé.
`train` vérifie d'abord les données, puis construit si nécessaire et lance
l'entraînement explicitement. Les autres services n'ont pas besoin d'être démarrés.

`prepare-training` classe les vidéos si nécessaire, extrait jusqu'à 24 images par
vidéo, lance **MegaDetector** et recadre les animaux. Le résultat est
`data/results/vision/training.json`, accompagné de `frames.json`, `detections.json`,
`crops.json` et `preparation.json`. Les erreurs de lecture/détection sont rapportées ;
une préparation partielle retourne un code non nul. Relancer recalcule les images
et détections, sans cache implicite.

Les poids réels du détecteur doivent être présents dans `data/models/md_v5a.0.0.pt`.
[Télécharger MDv5a depuis sa publication officielle](https://github.com/agentmorris/MegaDetector/releases/download/v5.0/md_v5a.0.0.pt)
et y enregistrer le fichier. Aucun téléchargement n'est lancé par les imports
ou par la préparation.

**Par défaut, Make autorise les labels provisoires issus des noms** pour démarrer
sur ce dataset majoritairement mono-espèce. MegaDetector localise les animaux ;
il ne détermine pas ces dix espèces. Les labels inconnus sont exclus. Les refus
humains sont toujours exclus et les corrections humaines priment sur le nom et
sur le quota de 18 recadrages par vidéo. `review.json`, lorsqu'il existe, est lu
lors de la préparation et n'est jamais remplacé par une fausse validation humaine.
Après une correction, relancer la préparation pour actualiser `training.json`.

Les ensembles sont séparés **par vidéo avant extraction** et les copies identiques
restent ensemble. Chaque classe doit avoir des exemples en train et val doit être
non vide. Le score de validation sert au choix du checkpoint ; il est **provisoire
si ses labels proviennent des noms**, avec `human_validated=false` dans l'historique
et `label_provenance` dans le checkpoint. Il ne constitue pas une évaluation
scientifique vérifiée. Les prises issues d'une même scène doivent être regroupées
pour une évaluation indépendante. La commande `evaluate` reste réservée aux labels
humains. Les imports Python restent stricts par défaut ; Make active explicitement
`training.allow_filename_labels`.

Pour entraîner uniquement sur une revue humaine :

```sh
make train DEVICE=cuda ALLOW_FILENAME_LABELS=0 MANIFEST=/storage/results/vision/review.json
```

Chaque run écrit `data/checkpoints/<run_id>/best.pt` et `last.pt` (reprise complète),
avec son historique sous `data/results/vision/training/<run_id>/`. Le fichier
historique `classifier_v3_best.pt` n'est pas remplacé automatiquement : sélectionner
le nouveau `best.pt` avec `CHECKPOINT=...` pour l'inférence. Le parcours `train`
sur CUDA soumet maintenant sa tâche à Redis et nécessite le worker ML démarré.
Sans checkpoint initial, les poids sont initialisés aléatoirement ; aucun transfert
ImageNet n'est téléchargé automatiquement. Exemple avec un checkpoint compatible :

```sh
make train DEVICE=cuda BATCH_SIZE=2 EPOCHS_HEAD=6 EPOCHS_FINETUNE=18 INITIAL_CHECKPOINT=/storage/checkpoints/initial.pt
```

Pour l'analyse, placer explicitement les poids MegaDetector dans
`data/models/md_v5a.0.0.pt`, puis déposer les vidéos dans **`data/datasets/inbox/`** :

```sh
make analyze DEVICE=cuda
make analyze DEVICE=cuda VIDEO="ma video.mp4"
make watch DEVICE=cuda
```

`analyze` traite les fichiers déjà déposés. `watch` reste actif au premier plan et
traite automatiquement les nouveaux dépôts ; arrêter avec **Ctrl+C**. Il attend
dix secondes sans changement de taille/mtime, réglables avec `STABLE_SECONDS=30`.
Pour une copie longue, copier sous un nom `video.mp4.part`, puis renommer en `.mp4`
une fois terminé : le suffixe `.part` est ignoré. La stabilité seule ne garantit
pas qu'une copie temporairement suspendue soit terminée.

Les résultats sont dans :

```text
data/results/vision/analyses/<nom>-<identifiant>/annotated.mp4
data/results/vision/analyses/<nom>-<identifiant>/report.json
data/results/vision/analyses/<nom>-<identifiant>/state.json
```

Les originaux restent dans inbox. `state.json` distingue `completed` et `error`.
Les analyses déjà terminées sont ignorées ; une modification du contenu vidéo,
des poids ou des paramètres produit une nouvelle identité. Les erreurs enregistrées
ne sont pas relancées en boucle. Pour réessayer explicitement :

```sh
make analyze DEVICE=cuda VIDEO="ma video.mp4" FORCE=1
```

Le verrou GPU couvre le chargement, le calcul et la libération des modèles. Une
analyse ponctuelle échoue si le GPU est déjà occupé par ces commandes ; `watch`
attend et réessaie. Les modèles sont libérés après chaque lot, pour permettre
l'entraînement pendant que la surveillance reste en attente. Redémarrer `watch`
après modification des paramètres ; les fichiers de poids sont relus pour chaque lot.

Variables Make : `DEVICE`, `VIDEO` (chemin relatif à inbox), `MANIFEST`, `DETECTOR`,
`CHECKPOINT`, `INITIAL_CHECKPOINT`, `ALLOW_FILENAME_LABELS` (1 par défaut),
`BATCH_SIZE`, `EPOCHS_HEAD`, `EPOCHS_FINETUNE`,
`FORCE`, `POLL_SECONDS` et `STABLE_SECONDS`. Les chemins de modèles/manifeste sont
ceux **dans le conteneur**, donc préfixés par `/storage/`. `DATA_ROOT` dans `.env`
permet de changer leur racine hôte. Le dossier inbox autorise le dépôt depuis un
compte hôte Linux avec un mode sticky ; il reste monté en lecture seule dans vision.
Les vidéos déposées doivent être lisibles par l'UID 10001.

L'export MP4 ne conserve pas l'audio et le codec `mp4v` n'est pas garanti dans
tous les navigateurs. Les observations restent des prédictions à valider.

## Prérequis

- Docker Engine et plugin Compose v2.24 ou supérieur, ou Docker Desktop récent,
  en mode conteneurs Linux. Docker doit pouvoir télécharger les images et les
  dépendances pendant la construction ; les services fonctionnent ensuite localement.
- Ports locaux 8000 et 8080 disponibles (modifiables dans `.env`).
- Aucun Python, Node, Make ou GPU nécessaire sur l'hôte pour le démarrage CPU.
- Prévoir plusieurs Go pour les images CPU, et au moins 15 Go supplémentaires
  disponibles pour télécharger et construire l'image PyTorch GPU, hors datasets.

Pour NVIDIA sous Linux : installer un pilote NVIDIA compatible, puis le
[NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html).
Configurer le runtime Docker avec `sudo nvidia-ctk runtime configure --runtime=docker`,
puis redémarrer Docker avec `sudo systemctl restart docker`.

Sous Windows : Windows 11 ou Windows 10 compatible WSL2, pilote NVIDIA Windows
avec support WSL, distribution WSL2 à jour (`wsl --update`), Docker Desktop avec
backend WSL2 et intégration de la distribution activés. Utiliser les conteneurs
Linux. Ne pas installer de pilote NVIDIA Linux dans WSL : le pilote est fourni
par Windows. Les commandes Docker ci-dessous fonctionnent aussi dans PowerShell ;
Make est facultatif. Pour les performances et permissions Linux, préférer un
checkout dans le système de fichiers WSL (`~/biosentinelle`) à `/mnt/c/...`.
Voir les [prérequis GPU Docker Desktop](https://docs.docker.com/desktop/features/gpu/)
et les [consignes NVIDIA WSL](https://docs.nvidia.com/cuda/wsl-user-guide/index.html).

L'image GPU est `pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime`, figée par digest ;
la [matrice officielle PyTorch](https://docs.pytorch.org/get-started/previous-versions/)
confirme la combinaison PyTorch 2.6 / CUDA 12.4. Utiliser un pilote récent ; comme
base conservatrice CUDA 12.4, NVIDIA indique Linux >= 550.54.14 et Windows >= 551.61
dans ses [notes CUDA 12.4](https://docs.nvidia.com/cuda/archive/12.4.0/cuda-toolkit-release-notes/index.html).
Un pilote plus récent peut exécuter ce runtime. Le CUDA Toolkit n'est pas requis
sur l'hôte. La RTX 3050 est compatible ; aucun modèle n'est chargé dans ses 4 Go.

## Démarrage CPU

Depuis la racine, facultativement copier `.env.example` vers `.env` :

```sh
cp .env.example .env
docker compose up -d --build --wait
docker compose ps -a
```

PowerShell : utiliser `Copy-Item .env.example .env` pour la copie. Sans `.env`,
`docker compose up -d` fonctionne avec les mêmes valeurs locales par défaut et
construit les images manquantes. Après modification du code, ajouter `--build`.

- Interface : <http://localhost:8080> ; elle affiche le statut réel de l'API.
- API : <http://localhost:8000/health> ; documentation : <http://localhost:8000/docs>.
- Depuis le navigateur : `/api/health` est relayé par Nginx vers `backend:8000/health`,
  sans URL Docker dans le navigateur ni configuration CORS supplémentaire.
- `storage-init` et `migrate` doivent terminer avec le code 0 ; les six services
  persistants doivent être `healthy`. La migration Alembic active `vector` avant
  le démarrage de l'API. `/health` renvoie 503 si PostgreSQL/pgvector ou Redis échoue.

## Démarrage et diagnostic GPU

Le fichier additionnel remplace uniquement l'image du worker vision et réserve
un GPU NVIDIA selon la [configuration Compose officielle](https://docs.docker.com/compose/how-tos/gpu-support/).
L'API, l'interface, PostgreSQL, Redis et le worker documentaire restent sur CPU.

```sh
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build --wait
docker compose -f docker-compose.yml -f docker-compose.gpu.yml exec vision nvidia-smi
docker compose -f docker-compose.yml -f docker-compose.gpu.yml exec vision python -m workers.vision.cuda_check
```

Diagnostic indépendant du démarrage des services (construit l'image si nécessaire) :

```sh
docker compose -f docker-compose.yml -f docker-compose.gpu.yml run --build --rm --no-deps vision nvidia-smi
docker compose -f docker-compose.yml -f docker-compose.gpu.yml run --build --rm --no-deps vision python -m workers.vision.cuda_check
```

Le second diagnostic teste `torch.cuda.is_available()`, alloue deux valeurs,
effectue un calcul CUDA et synchronise le GPU. Il échoue explicitement si CUDA
est absent, et imprime les versions et le nom du GPU en cas de succès.
Le worker effectue ce même contrôle une seule fois au démarrage GPU ; ses sondes
suivantes vérifient son signal de vie Redis, sans calcul périodique sur le GPU.
`nvidia-smi` seul ne prouve pas que PyTorch peut exécuter un calcul CUDA.

Pour vérifier uniquement la transmission du GPU à Docker avec une image plus légère :

```sh
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

Retour CPU : `docker compose up -d --build --wait vision`. Ne pas augmenter
le nombre de répliques vision : la configuration prévoit un seul processus.
Il ne consomme encore aucune tâche. Les opérations explicites du package vision
utilisent déjà un verrou interprocessus ; leur raccordement à une file de tâches
reste à implémenter.

## Stockage et réseau

```text
backend/                 API, configuration et migrations Alembic
frontend/                Vue, TypeScript, Vite ; Nginx dans l'image finale
workers/vision/          attente supervisée ; diagnostic CUDA explicite
workers/documents/       attente supervisée indépendante
shared/                  signal de vie et supervision des workers
infra/                   Nginx, initialisation des répertoires, dépendances de test
tests/                   tests CPU, intégration et test GPU facultatif
data/                    fichiers persistants, ignorés par Git et les builds
```

Les montages locaux sont distincts sous `DATA_ROOT` :

| Répertoire hôte | Chemin conteneur | Usage prévu |
| --- | --- | --- |
| `datasets/` | `/storage/datasets` | Vidéos et images ; lecture seule pour API et vision |
| `models/` | `/storage/models` | Poids et caches ; lecture seule dans l'API |
| `checkpoints/` | `/storage/checkpoints` | Checkpoints ; lecture seule dans l'API |
| `documents/` | `/storage/documents` | Documents ; API et worker documentaire |
| `results/` | `/storage/results` | Résultats ; API et workers |

`storage-init` crée seulement ces répertoires et les caches, avec UID/GID 10001
pour les processus Python non root. Il ne parcourt pas les données existantes.
Sous Linux, les fichiers ajoutés manuellement doivent être lisibles par cet UID ;
les répertoires où une écriture est attendue doivent lui être accessibles.
Les vidéos existantes dans `video datathon/` et le notebook restent intacts ;
aucune copie ni ingestion automatique n'est effectuée.

PostgreSQL et Redis utilisent respectivement les volumes Docker nommés
`biosentinelle_postgres-data` et `biosentinelle_redis-data` (préfixe personnalisable).
Le réseau `services` est interne et aucune publication de leurs ports n'est définie.
Le réseau `web` relie le frontend à l'API. Seuls les ports frontend et API sont
publiés, sur `127.0.0.1`. Les workers n'ont pas d'accès Internet sur leur réseau
d'exécution. Les modèles devront être provisionnés explicitement.

Redis utilise AOF avec synchronisation chaque seconde et `noeviction` pour ne pas
évincer les futures tâches. Une panne brutale peut perdre environ une seconde
d'écritures ; cette configuration ne garantit pas l'exécution exactement une fois.
La politique n'est pas un plafond mémoire : prévoir une limite adaptée quand les
vraies files et leurs tailles seront connues. Les sondes des workers sont des
clés temporaires, pas des tâches ni des résultats d'analyse.

Les chemins de stockage sont centralisés dans l'environnement et les montages.
Le package vision expose un contrat de stockage et un adaptateur local avec
écritures atomiques ; aucun accès S3 n'est implémenté.

## Variables d'environnement

Le fichier `.env` sert à l'interpolation Compose ; il n'est pas copié dans les images.
Les valeurs locales d'exemple conviennent uniquement à un poste de développement.

| Variable | Défaut | Description |
| --- | --- | --- |
| `COMPOSE_PROJECT_NAME` | `biosentinelle` | Préfixe des ressources Docker |
| `BACKEND_PORT` | `8000` | Port hôte de FastAPI |
| `FRONTEND_PORT` | `8080` | Port hôte du frontend |
| `POSTGRES_DB` | `biosentinelle` | Base applicative |
| `POSTGRES_USER` | `biosentinelle` | Utilisateur local et propriétaire des migrations |
| `POSTGRES_PASSWORD` | `biosentinelle_local` | Mot de passe local ; changer avant la première initialisation |
| `DATA_ROOT` | `./data` | Racine persistante hôte, relative au fichier Compose |
| `WORKER_HEARTBEAT_SECONDS` | `5` | Intervalle du signal de vie |
| `WORKER_HEARTBEAT_MAX_AGE_SECONDS` | `30` | Délai de santé, strictement supérieur à deux intervalles |
| `VISION_DEVICE` | `cpu` | Périphérique des opérations explicites vision ; le fichier GPU impose `cuda` |

Variables internes définies par Compose : `POSTGRES_HOST=postgres`,
`POSTGRES_PORT=5432`, `REDIS_URL=redis://redis:6379/0`, `STORAGE_ROOT=/storage`,
`TORCH_HOME=/storage/models/cache/torch`, `HF_HOME=/storage/models/cache/huggingface`,
`XDG_CACHE_HOME=/storage/models/cache`. `REQUIRE_CUDA` vaut 0 sur CPU et 1 sur GPU ;
`NVIDIA_DRIVER_CAPABILITIES=compute,utility` est limité au worker GPU.
Les tests d'intégration utilisent `BASE_URL` et `FRONTEND_URL` vers les services Docker.

Changer les identifiants PostgreSQL dans `.env` ne modifie pas un volume déjà
initialisé : faire une rotation SQL explicite, sans supprimer les données.

## Vérifications et tests

Les tests unitaires ne nécessitent ni services actifs ni GPU :

```sh
docker compose config --quiet
docker compose -f docker-compose.yml -f docker-compose.gpu.yml config --quiet
docker compose --profile test run --build --rm tests
docker compose --profile test run --build --rm tests ruff check backend shared workers tests infra/init_storage.py
```

Après un démarrage avec `--wait`, tests réels PostgreSQL/pgvector/Alembic,
persistance Redis configurée, signaux de vie des deux workers et proxy HTTP :

```sh
docker compose --profile test run --build --rm tests pytest -m integration
docker compose exec redis redis-cli ping
```

Vérification PostgreSQL avec les identifiants par défaut (adapter en cas de changement) :

```sh
docker compose exec postgres psql -U biosentinelle -d biosentinelle -c "SELECT extname, extversion FROM pg_extension;"
```

Le diagnostic CUDA est le test GPU autonome recommandé. Pour une exécution pytest
dans un environnement Python disposant déjà de PyTorch CUDA et des dépendances
de test : `pytest -m gpu`. Les tests CPU excluent explicitement les marqueurs
`integration` et `gpu` ; un test GPU demandé explicitement échoue si CUDA est absent.
Le build frontend exécute `vue-tsc --noEmit` avant Vite.

Raccourcis Make (Linux/WSL avec GNU Make) : `make up`, `make gpu`, `make test`,
`make integration`, `make lint`, `make gpu-check`, `make nvidia-smi`, `make down`.

## Maintenance locale

```sh
docker compose logs --tail=100 backend migrate vision documents
docker compose run --rm migrate
docker compose exec backend alembic -c backend/alembic.ini current
docker compose down
```

`down` préserve les volumes et `data/`. `down -v` détruit les volumes PostgreSQL
et Redis : réserver cette option à une réinitialisation volontaire après sauvegarde.
Après une nouvelle migration, exécuter `docker compose run --rm migrate` puis
redémarrer l'API. Les dépendances de santé ordonnent le démarrage ; elles ne
redémarrent pas automatiquement les autres services quand une dépendance devient
malade. L'API reflète alors la panne dans `/health`, et les workers redémarrent
si leur connexion Redis provoque une sortie du processus.

Les dépendances directes sont dans les fichiers `requirements.in`, les versions
transitives figées dans `requirements.txt`, et les dépendances frontend dans
`package-lock.json` (`npm ci` au build). Pour une mise à jour Python volontaire,
utiliser `uv==0.8.22`, puis `uv pip compile <fichier.in> --python-version 3.12
--universal --output-file <fichier.txt>` et relancer les tests. Ne pas éditer
les verrous à la main. Les images ont des versions explicites ; pgvector et
PyTorch ont aussi un digest pour figer leurs composants embarqués.

Le notebook reste une référence fonctionnelle, avec des dépendances Colab/Drive
qui ne sont pas exécutées par cette infrastructure. Aucun résultat ML n'est
annoncé comme fonctionnel. Les 10 espèces de la consigne utilisateur font foi ;
les noms de vidéos ne constituent pas des labels fiables pour chaque animal.

## Validation réalisée le 21 octobre 2026

- Démarrage CPU réel sous Docker Desktop : six services persistants sains,
  initialisation du stockage et migrations terminées avec le code 0.
- 12 tests unitaires et 3 tests d'intégration réussis ; Ruff et formatage validés.
- Build Vue/TypeScript/Vite réussi ; audit npm sans vulnérabilité signalée.
- Après redémarrage PostgreSQL/Redis : migration conservée, clé témoin Redis
  conservée puis supprimée, retour de tous les services à l'état sain.
- `nvidia-smi` dans le conteneur CUDA léger : RTX 3050 de 4 Go visible,
  pilote hôte 592.00.
- Image PyTorch GPU non construite et calcul PyTorch CUDA non exécuté ici :
  environ 11 Go libres sur le disque hôte, sous le budget de 15 Go retenu pour
  ce build. La configuration GPU fusionnée est validée par `docker compose config` ;
  la commande `workers.vision.cuda_check` reste à exécuter après libération d'espace.
