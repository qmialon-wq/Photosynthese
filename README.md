# BioSentinelle Normandie

Socle local Docker : FastAPI, Vue 3 + TypeScript + Vite, PostgreSQL 16 avec
pgvector 0.8.1, Redis et deux workers Python indépendants. Aucun modèle, analyse
vidéo, entraînement, ingestion documentaire ou RAG n'est implémenté ici.

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

Retour CPU : `docker compose up -d --build --wait vision`. Ne pas augmenter
le nombre de répliques vision : la configuration prévoit un seul processus.
Il ne consomme encore aucune tâche ; le verrou d'exécution des futures tâches
GPU devra être ajouté avec le véritable système de tâches, avant tout pipeline.

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
Aucun accès S3 n'est implémenté à cette étape ; une interface de stockage devra
accompagner les premiers vrais usages de fichiers, sans dépendre des chemins hôte.

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
docker compose exec postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT extversion FROM pg_extension WHERE extname = '\''vector'\'';"'
docker compose exec redis redis-cli ping
```

La commande `psql` ci-dessus est destinée au shell Linux/WSL. Alternative simple,
avec les identifiants par défaut, compatible PowerShell :

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
