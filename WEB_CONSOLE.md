# Console web BioSentinelle

L'interface Vue 3 / TypeScript utilise Vue Router et PrimeVue, sans calcul ML
dans le navigateur. PostgreSQL et les fichiers gérés par les workers restent
les sources de vérité. Le navigateur mémorise uniquement un identifiant local automatique ;
les liens conservent les identifiants de tâches pour retrouver un résultat
après rechargement.

## Lancer

Depuis la racine du dépôt :

```sh
make detector-fetch
make review-up DEVICE=cuda
# Variante CPU, sans exigence de GPU :
make review-up DEVICE=cpu
```

Ouvrir <http://localhost:8080>. Les migrations jusqu'à `0004_web_console`
sont appliquées avant le démarrage de l'API et du consommateur ML.
`docker compose up -d --build --wait` démarre l'interface, l'API et les bases,
mais ne consomme pas les tâches ML. Dans ce mode, les traitements soumis
restent en attente jusqu'au lancement de `review-up`.

Aucun nom de revue n'est demandé. Un identifiant `local-<uuid>` est créé au premier
appel API et conservé dans ce navigateur pour tracer les actions. Les appels API
sans `X-Reviewer` sont attribués à `local` ; les clients existants peuvent toujours
fournir cet en-tête. Cette attribution est déclarative, sans identité authentifiée.
La séparation des espaces organise la navigation et ne constitue pas un contrôle
d'accès : aucune authentification distante ni gestion de rôles n'est ajoutée.

L'accueil `/` donne accès à **Vidéothèque**, **Analyses** et **Validation humaine**.
Le lien **Administration** ouvre `/admin` et ses pages de gestion ; le lien
**Espace observation** permet de revenir. Les anciens liens `/training`, `/datasets`,
`/models` et `/evaluation` redirigent vers `/admin/...`, en conservant leurs paramètres.

## Parcours disponibles

1. **Accueil** : trois actions principales et les cinq dernières analyses réelles.
   **Vue d'ensemble administrative** (`/admin`) : compteurs réels des vidéos uniques par contenu, espèces validées,
   recadrages à revoir, tâches de la console et dernier entraînement SQL.
   Un état vide ou « Non mesuré » remplace toute mesure absente. Le nom du
   run permet notamment d'identifier les entraînements de test existants.
2. **Vidéothèque** : sélectionner un fichier depuis l'ordinateur. L'indexation d'une vidéo déjà
   présente dans `data/datasets/inbox` est disponible dans `/admin/videos`. Le transfert utilise des requêtes de
   4 Mio maximum, puis le worker assemble, vérifie, sonde et prépare une
   prévisualisation H.264. Le fichier source reste intact. Le transfert peut
   être annulé. Recherche, espèce provisoire, disponibilité et pagination
   s'appuient sur l'API. La bibliothèque inclut les vidéos de la revue existante.
3. **Analyses** : choisir l'objectif (identifier les espèces avec le modèle actif,
   ou détecter seulement), puis le détail : équilibré (une image sur 2), détaillé
   (chaque image), rapide (une image sur 10, susceptible de manquer un passage bref).
   L'identification est proposée par défaut lorsqu'un modèle est actif ; sinon un
   message explique la disponibilité de la détection seule. Les seuils distincts
   et le nombre minimal de détections par piste se règlent dans `/admin/analyses`.
   Les compteurs d'images sont publiés au traitement ;
   le chargement des modèles et l'encodage restent indéterminés. Le résultat
   contient le MP4 H.264, le JSON intégral, les localisations et les scores
   distincts. Les 200 premières détections apparaissent dans le tableau.
   Une analyse sans détection reste un résultat valide.
4. **Validation humaine** : utiliser « Préparer les recadrages à valider »
   depuis une vidéo pour soumettre une détection distincte. La galerie filtre
   les états, espèces, indicateurs de qualité et éventuellement une vidéo.
   Dessiner une boîte sur l'image originale ou utiliser les flèches et les
   champs xywh normalisés. Choisir explicitement l'espèce avant confirmation ;
   le commentaire est facultatif, y compris pour rejeter ou rouvrir une annotation.
   Les cases permettent de sélectionner plusieurs images ou toute la page (24 images),
   puis d'attribuer une espèce commune ou de rejeter la sélection. Les boîtes sont
   conservées ; leur correction reste individuelle. La sélection est réinitialisée
   lors d'un changement de page ou de filtre. Les noms de fichiers restent provisoires.
   Un lot est atomique : un conflit annule toutes ses modifications, sans validation
   partielle. L'API contrôle les révisions concurrentes et le
   gel du test. L'historique et les anciens recadrages sont conservés.
5. **Datasets** : construire une version asynchrone, consulter les effectifs
   par espèce/split et les indicateurs de qualité, télécharger ou reconstruire
   son archive. Les exclusions choisies sont enregistrées. Les protections
   décrites dans [HUMAN_REVIEW.md](HUMAN_REVIEW.md) restent applicables.
6. **Entraînements** : choisir un dataset exporté, un backbone, les paramètres
   de batch/accumulation, AMP, early stopping et les deux phases. Le backend
   exige les dix classes validées dans train et une validation non vide.
   Le worker extrait et vérifie l'archive versionnée, entraîne le vrai modèle
   puis enregistre le meilleur checkpoint. Les métriques réelles sont publiées
   à chaque époque ; les journaux montrent les événements du worker. L'arrêt
   est coopératif, aux points d'interruption disponibles, sans tuer le worker.
   Le dernier checkpoint reste disponible pour la reprise CLI existante.
7. **Modèles** : enregistrer un `.pt` existant dans `data/checkpoints`, avec
   vérification asynchrone des classes, du backbone et du `state_dict`.
   Les versions sont identifiées par SHA-256. Une sélection explicite définit
   le modèle actif pour les prochaines analyses de la console. Chaque tâche
   fige sa version et son empreinte ; une activation ultérieure ne la change
   pas. Les CLI historiques continuent à utiliser leur configuration.
8. **Évaluation** : consulter les mesures réellement enregistrées avec un
   checkpoint ou lancer une évaluation sur un dataset/split choisi. Accuracy,
   macro-F1, matrice et confusions sont affichées uniquement lorsqu'elles
   existent. Les mesures vidéo nécessitent une vérité vidéo validée ; elles
   ne sont pas déduites du nom des fichiers.

Le fine-tuning du détecteur n'est pas présenté comme une fonction disponible
de cet écran d'entraînement : celui-ci concerne le classificateur.
Une correction d'annotation ne soumet aucun entraînement.

## API et stockage

Les routes `/api/console/*` du frontend sont transmises au backend sous
`/console/*`. Les API de revue et d'entraînement existantes sont réutilisées.
La documentation des schémas se trouve dans <http://localhost:8000/docs>.

Les tables `console_uploads`, `console_chunks`, `console_videos`,
`console_tasks`, `console_logs` et `console_models` conservent les transferts,
sources, états, demandes d'arrêt, résultats et versions. Une outbox PostgreSQL
alimente la même file Redis et le même consommateur unique. Les identifiants
de tâches et les verrous empêchent de retraiter un message déjà terminé.

- Blocs reçus : `data/results/uploads/<uuid>/`.
- Vidéos assemblées : `data/datasets/inbox/<uuid>/<nom_original>`.
- Prévisualisations : `data/results/vision/console/previews/`.
- Analyses : `data/results/vision/console/analyses/<tâche>/`.
- Datasets matérialisés pour le worker : `data/results/vision/console/datasets/`.
- Checkpoints : `data/checkpoints/<tâche>/`, persistants après redémarrage.

Le backend écrit les petits blocs dans results ; le worker assemble la vidéo
dans datasets. Le montage datasets du backend reste en lecture seule. FFmpeg
est installé dans les images ML et l'image de test, sans CUDA ajouté à l'API.

Limites explicites : 20 Gio maximum par fichier, pas de reprise automatique
d'un transfert après fermeture du navigateur, pas de nettoyage automatique
des blocs annulés, du cache ou des archives. Les listes de tâches montrent
les 50 dernières entrées ; le journal affiche les 500 derniers événements.
Les anciennes tâches Redis soumises par les CLI restent consultables par leur
API historique ; leurs runs SQL apparaissent dans Entraînements.

Les sources originales ayant un codec non lisible par le navigateur peuvent
être téléchargées. Les nouveaux imports de la console et MP4 annotés sont
réencodés en H.264 sans audio pour la consultation. Aucun modèle n'est
téléchargé ni entraîné au démarrage de la page.

## Développement et vérification

Node 22.22.2 ou une version compatible plus récente est nécessaire pour les
outils de développement. Le build Docker utilise une image Node fixée.
Sous PowerShell, utiliser `npm.cmd` si la politique d'exécution bloque `npm.ps1`.

```sh
cd frontend
npm ci
npm run dev
npm run build
npm run test
npx playwright install chromium
npm run test:e2e
```

Le serveur Vite utilise le port 5173 et relaie `/api` vers `localhost:8000`.
Les tests Playwright démarrent leur propre serveur au port 4173. Ils simulent
les réponses HTTP **uniquement dans les tests** : import/analyse, correction
après rechargement, entraînement/arrêt, métriques/mobile et contrôle axe WCAG AA.
Il n'existe aucun mode de simulation dans l'application.

Depuis la racine, `make web-test` et `make web-e2e` lancent ces vérifications.
Si nécessaire sous Windows, ajouter `NPM=npm.cmd`.

```sh
make test
make integration
# Facultatif : vrai entraînement PyTorch CPU de deux phases sur fixtures synthétiques :
make web-training-test
```

Le dernier test nécessite PostgreSQL démarré et construit une image de test
PyTorch CPU. Il passe par l'API, un véritable export de dataset, le worker,
les checkpoints et le registre des modèles. Les tests PostgreSQL utilisent
des schémas isolés et ne valident aucune donnée réelle de l'utilisateur.

Un test navigateur facultatif peut exercer le vrai backend et le vrai worker :

```powershell
# Depuis frontend, avec Compose ML démarré et les poids locaux présents :
$env:E2E_BASE_URL = 'http://localhost:8080'
$env:BIOSENTINELLE_LIVE_VIDEO = 'C:/chemin/vers/une-courte-video.mp4'
# Facultatif, après activation d'un vrai classificateur dans Modèles :
$env:BIOSENTINELLE_LIVE_CLASSIFY = '1'
npm.cmd run test:e2e -- tests/e2e/live.spec.ts
```

Ce test importe réellement le fichier, lance une analyse, vérifie la lecture
du MP4 et télécharge son JSON. Ses données restent dans les volumes, sous
l'acteur `diagnostic-navigateur`, sans validation humaine automatique.
