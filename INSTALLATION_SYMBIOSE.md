# Installer et lancer Symbiose sur un ordinateur

> Guide pour les membres de l'équipe Symbiose — dépôt : https://github.com/qmialon-wq/Photosynthese
>
> Ce guide décrit le **démarrage local CPU** prévu par le `README.md` du projet. Il ne configure pas les fonctions avancées d'entraînement GPU, les modèles optionnels ni un serveur public.

## 1. Prérequis

- Une connexion Internet lors du premier lancement (téléchargement des images et dépendances).
- **Git** : https://git-scm.com/downloads
- **Docker Desktop** pour Windows/macOS : https://www.docker.com/products/docker-desktop/ ; ou Docker Engine avec le plugin Compose sur Linux.
- Docker Compose **v2.24 ou plus récent** ; Docker Desktop récent convient.
- Plusieurs Go d'espace disque disponibles ; les ports **8080** (interface) et **8000** (API) doivent être libres.
- **Aucun Python, Node.js, GNU Make ni GPU NVIDIA requis** pour le lancement CPU de base.

**Windows :** utiliser Windows 10/11 compatible WSL2, Docker Desktop avec le moteur Linux/WSL2, et **PowerShell**. Démarrer Docker Desktop avant de lancer les commandes.

**macOS/Linux :** utiliser un terminal ; sur Linux, vérifier que le service Docker fonctionne et que votre utilisateur peut exécuter `docker` (selon la configuration, `sudo` peut être nécessaire).

Vérifier les outils :

```sh
git --version
docker --version
docker compose version
docker info
```

Si `docker info` échoue, démarrer Docker Desktop (ou le démon Docker sous Linux) avant de continuer.

## 2. Télécharger le projet (une seule fois par ordinateur)

Ouvrir un terminal dans le dossier où vous souhaitez installer le projet, puis exécuter :

```sh
git clone https://github.com/qmialon-wq/Photosynthese.git
cd Photosynthese
```

**Important :** `git clone` récupère le dépôt pour la première fois ; `git pull` sert à mettre à jour une copie déjà existante. **Ne pas relancer `git clone` dans un dossier Photosynthese déjà présent.**

Sous Windows, on peut aussi ouvrir l'Explorateur de fichiers dans le dossier `Photosynthese`, saisir `powershell` dans sa barre d'adresse et appuyer sur Entrée.

Vérifier que `docker-compose.yml`, `.env.example`, `frontend/` et `backend/` sont présents.

## 3. Préparer la configuration locale

Le fichier `.env` est facultatif selon le dépôt : Docker Compose possède des valeurs par défaut. Il est néanmoins pratique pour personnaliser les ports et conserver la configuration locale.

**Windows (PowerShell)** :

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

**macOS / Linux** :

```sh
[ -f .env ] || cp .env.example .env
```

Les valeurs par défaut exposent l'interface sur `http://localhost:8080` et l'API sur `http://localhost:8000`.

**Ne pas publier son `.env` ni ses jetons d'initialisation sur GitHub.** Pour un usage exposé à Internet, il faut revoir les mots de passe, les paramètres de sécurité et l'architecture réseau : ce guide ne traite que du local.

## 4. Créer le réseau Docker `web` (une seule fois)

Le projet utilise un réseau Docker externe appelé `web`. Il doit exister avant le lancement.

**Windows (PowerShell)** :

```powershell
docker network inspect web
```

Si la commande indique que le réseau n'existe pas :

```powershell
docker network create web
```

**macOS / Linux** :

```sh
docker network inspect web >/dev/null 2>&1 || docker network create web
```

Si le réseau existe déjà, ne pas le recréer.

## 5. Construire et démarrer Symbiose

Depuis la **racine du dépôt** (le dossier contenant `docker-compose.yml`) :

```sh
docker compose up -d --build --wait
```

Cette commande construit les images nécessaires, lance les conteneurs en arrière-plan et attend les contrôles de santé. Le premier lancement peut prendre plusieurs minutes.

Pour voir l'état des services :

```sh
docker compose ps -a
```

Les services persistants (`frontend`, `backend`, `postgres`, `redis`, `vision`, `documents`) doivent être en état **healthy**. Les tâches ponctuelles `storage-init` et `migrate` doivent s'être terminées avec le **code 0**.

## 6. Ouvrir l'application

- **Interface Symbiose** : http://localhost:8080
- **État de l'API** : http://localhost:8000/health
- **Documentation interactive de l'API** : http://localhost:8000/docs

Ces adresses désignent **l'ordinateur qui exécute Docker**. `localhost` sur un autre PC ne pointe pas vers le premier PC.

### Première utilisation : créer un administrateur

Sur une installation neuve, ouvrir :

http://localhost:8080/initialisation

L'application demande un **jeton d'initialisation** créé localement. Depuis le dossier `Photosynthese` :

**Windows (PowerShell)** :

```powershell
Get-Content .\data\results\auth\bootstrap-token
```

**macOS / Linux** :

```sh
cat data/results/auth/bootstrap-token
```

Saisir le jeton **dans le formulaire local**, puis choisir une adresse e-mail et un mot de passe administrateur. **Ne pas envoyer ce jeton dans une discussion ni le publier.** Une fois le compte créé, se connecter depuis l'interface.

> Chaque installation neuve possède sa propre base de données et ses propres comptes. `git clone` ne transfère **pas** les utilisateurs, les données ni les volumes Docker d'un autre ordinateur.

## 7. Utilisation quotidienne

Ouvrir Docker Desktop (Windows/macOS), puis un terminal dans `Photosynthese`.

**Démarrer sans reconstruire** :

```sh
docker compose up -d
```

**Afficher les services** :

```sh
docker compose ps -a
```

**Arrêter sans effacer les données** :

```sh
docker compose down
```

**Voir les journaux** :

```sh
docker compose logs --tail=100
```

**Suivre les journaux en direct** (`Ctrl+C` pour quitter l'affichage) :

```sh
docker compose logs -f --tail=100
```

**Attention :** ne pas utiliser `docker compose down -v` sans avoir sauvegardé les données : l'option `-v` supprime les volumes Docker du projet, dont les données persistantes de PostgreSQL et Redis.

## 8. Mettre à jour l'application

Depuis le dossier du projet :

```sh
git status
git pull
```

Si Git signale des modifications locales, les sauvegarder ou demander conseil avant de poursuivre ; ne pas les écraser automatiquement.

Reconstruire et relancer ensuite les services :

```sh
docker compose up -d --build --wait
```

Le fichier `.env` et les données locales ne sont pas destinés à être synchronisés via Git.

## 9. Dépannage

### Le navigateur n'ouvre pas `http://localhost:8080`

1. Vérifier que Docker fonctionne : `docker info`.
2. Vérifier les conteneurs : `docker compose ps -a`.
3. Relancer : `docker compose up -d --build --wait`.
4. Lire les erreurs : `docker compose logs --tail=100`.
5. Tester l'API séparément : http://localhost:8000/health.

### Erreur « network web declared as external, but could not be found »

```sh
docker network create web
```

Puis relancer la commande de l'étape 5.

### Le port 8080 ou 8000 est déjà utilisé

Modifier les valeurs dans `.env`, par exemple :

```dotenv
FRONTEND_PORT=8081
BACKEND_PORT=8001
```

Puis redémarrer :

```sh
docker compose up -d --build --wait
```

L'interface devient alors `http://localhost:8081`. **Si le port du frontend change, mettre également à jour `AUTH_ALLOWED_ORIGINS` dans `.env` pour autoriser la nouvelle origine**, par exemple `http://localhost:8081` et `http://127.0.0.1:8081`, tout en conservant les autres origines nécessaires.

### `docker compose` n'est pas reconnu

Installer ou mettre à jour Docker Desktop (ou le plugin Compose sous Linux), puis rouvrir le terminal.

### Un service est `unhealthy` ou `exited`

```sh
docker compose ps -a
docker compose logs --tail=100
```

Identifier le service concerné dans les journaux. Le premier démarrage peut être long ; vérifier aussi la mémoire et l'espace disque disponibles.

### La page de connexion apparaît, mais les identifiants de l'autre PC ne fonctionnent pas

C'est normal sur une **nouvelle installation** : la base PostgreSQL locale ne contient pas automatiquement les comptes de l'autre PC. Utiliser la procédure d'initialisation de la section 6, si aucun administrateur n'existe encore. Si l'installation a déjà un administrateur, suivre la procédure de gestion des comptes du projet plutôt que réinitialiser les volumes.

## 10. Récapitulatif rapide

Pour un **nouvel ordinateur**, après installation de Git et Docker :

**Windows PowerShell** :

```powershell
git clone https://github.com/qmialon-wq/Photosynthese.git
cd Photosynthese
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
if (-not (docker network ls --format '{{.Name}}' | Where-Object { $_ -eq 'web' })) { docker network create web }
docker compose up -d --build --wait
docker compose ps -a
```

**macOS / Linux** :

```sh
git clone https://github.com/qmialon-wq/Photosynthese.git
cd Photosynthese
[ -f .env ] || cp .env.example .env
docker network inspect web >/dev/null 2>&1 || docker network create web
docker compose up -d --build --wait
docker compose ps -a
```

Puis ouvrir **http://localhost:8080**.

---

**Référence technique :** [`README.md` du dépôt Photosynthese](https://github.com/qmialon-wq/Photosynthese/blob/main/README.md), sections « Prérequis » et « Démarrage CPU ». Les commandes sont destinées à une installation locale ; elles peuvent évoluer avec le dépôt.
