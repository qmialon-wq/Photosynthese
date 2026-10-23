# Veille scientifique BioSentinelle

Le service découvre des publications réelles dans OpenAlex, Crossref et Europe PMC,
conserve leurs métadonnées et, sur demande, importe les textes accessibles dont
les droits sont établis. Il fonctionne sur CPU, indépendamment de la file vision.
Aucun modèle, LLM, embedding, recommandation ou écran web documentaire n'est ajouté.

## Démarrer et rechercher

Depuis la racine du dépôt, avec le fichier `.env` habituel :

```sh
make documents-up
make documents-search ARGS='--species "Vulpes vulpes" --topic ecology --limit 5'
make documents-status ARGS='<identifiant-de-tache>'
docker compose logs --tail=100 documents
```

`documents-up` construit backend et worker, applique Alembic et attend les
healthchecks. Il ne redémarre pas le worker vision. Un démarrage complet reste
possible avec `docker compose up -d --build`. Aucun GPU n'est requis.

Les commandes de recherche soumettent une tâche durable à PostgreSQL, publiée
dans le stream Redis `biosentinelle:documents:jobs`. Le worker effectue les appels,
le téléchargement et l'extraction hors des requêtes HTTP. L'API renvoie `202`,
un UUID et `status_url`. Une erreur sur une source ou une notice ne supprime pas
les résultats des autres. Les tâches sont `queued`, `running`, `completed`,
`partial` ou `error` ; chaque passage possède des événements consultables.

Pour obtenir également les copies autorisées :

```sh
make documents-search ARGS='--species "Vulpes vulpes" --sources openalex europepmc --limit 5 --download-fulltext'
```

Les options répétables `--species`, `--habitat`, `--territory`, `--topic` construisent
les requêtes. Utiliser les noms scientifiques, par exemple `Capreolus capreolus`,
`Sus scrofa`, `Vulpes vulpes`, et les termes du domaine en français ou en anglais.
Exemple ciblé : `--species "Vulpes vulpes" --habitat bocage --territory Normandy`.
La recherche est lexicale : un résultat ne prouve ni sa pertinence écologique ni
son applicabilité en Normandie. Les filtres géographiques peuvent réduire fortement
les résultats ; la validation humaine reste distincte de l'ingestion.

## Veilles périodiques

```sh
make documents-watch ARGS='--name renard-bocage --species "Vulpes vulpes" --topic habitat --interval 86400 --enabled'
docker compose exec -T documents python -m workers.documents.cli run-watch <identifiant-de-veille>
```

Sans `--enabled`, une veille est enregistrée mais n'est pas planifiée. Réutiliser
le même nom met sa configuration à jour et permet de la désactiver en omettant
`--enabled`. Intervalle minimal : 60 secondes. L'ordonnanceur tourne dans le worker
avec un verrou PostgreSQL et une clé unique par échéance ; il ne crée aucune veille
au démarrage et ne rejoue pas toutes les échéances manquées après un arrêt.

Les publications sont dédupliquées par DOI normalisé, identifiants de source et
SHA-256 des fichiers. Un DOI découvert tardivement rapproche les notices déjà
importées ; les anciennes identités restent redirigées et les historiques conservés.
Des DOI contradictoires déclenchent une erreur explicite plutôt qu'une fusion forcée.
Une observation identique ne duplique pas sa provenance. Les nouvelles observations
conservent leur source, réponse originale, empreinte et date.

La publication Redis utilise une outbox SQL. Les redélivrances ne réexécutent pas
une tâche terminée. Les messages abandonnés sont récupérés après 30 secondes ;
trois reprises d'une tâche interrompue sont autorisées. Une tâche terminée en erreur
se relance explicitement avec `POST /documents/tasks/{id}/retry` : nouveau passage,
réutilisation du cache et des fichiers, historique précédent préservé.

## Imports manuels

Déposer un PDF, TXT ou Markdown dans `data/documents/inbox/` (ou sous
`${DATA_ROOT}/documents/inbox/`) puis :

```sh
make documents-import ARGS='rapport.pdf --title "Rapport local" --rights-confirmed'
```

Ajouter `--doi` et `--license` quand ces informations sont connues. La confirmation
explicite des droits est obligatoire. Une licence inconnue n'est jamais déduite de
la présence du fichier : l'autorisation locale déclarée est enregistrée avec l'acteur.
Le fichier original reste dans `inbox`; une copie vérifiée est conservée dans `assets`.

Pour transférer un fichier depuis une machine cliente, envoyer son contenu binaire
brut (pas de formulaire multipart) :

```sh
curl --fail-with-body -X POST 'http://localhost:8000/documents/upload?filename=rapport.pdf&rights_confirmed=true' -H 'Content-Type: application/pdf' -H 'X-Reviewer: ecologue-local' --data-binary @rapport.pdf
```

Sous PowerShell utiliser `curl.exe`. Le transfert est borné ; l'extraction, le hash
et la déduplication se déroulent dans le worker. Les chemins absolus et les remontées
hors de `inbox` sont refusés. Les formats Word et les PDF nécessitant de l'OCR ne
sont pas pris en charge à cette étape.

## API et validation humaine

Voir également http://localhost:8000/docs. Les routes sont préfixées par `/documents` :

| Route | Fonction |
| --- | --- |
| `POST /search` | Recherche asynchrone ; `species`, `habitats`, `territories`, `topics`, `sources`, `limit_per_source`, `download_fulltext` |
| `POST /watches`, `GET /watches` | Enregistrer/modifier une veille par nom ; consulter les veilles |
| `POST /watches/{id}/run` | Déclencher un passage explicite |
| `POST /import`, `POST /upload` | Import local ou transfert brut, avec droits confirmés |
| `GET /tasks`, `GET /tasks/{id}` | État, résultat, compteurs, erreurs, dates et tentatives |
| `GET /tasks/{id}/events?after=0` | Journal paginé par identifiant croissant |
| `POST /tasks/{id}/retry` | Nouveau passage après une tâche terminée |
| `GET /?status=indexed&approved_only=true` | Documents indexés et acceptés pour pertinence **et** qualité |
| `GET /{id}` | Métadonnées, sources, fichiers, droits et historique des décisions |
| `POST /{id}/review` | Décision humaine, acteur, date et commentaire facultatif |
| `POST /{id}/fetch` | Récupérer/indexer une copie autorisée, ou réutiliser le fichier existant |
| `GET /{id}/pages`, `GET /{id}/chunks` | Texte, pages/références, passages et offsets |
| `GET /{id}/assets/{asset_id}` | Original conservé |

Exemple PowerShell :

```powershell
$body = @{species=@('Vulpes vulpes'); habitats=@('bocage'); sources=@('openalex','crossref','europepmc'); limit_per_source=5; download_fulltext=$false} | ConvertTo-Json
$job = Invoke-RestMethod http://localhost:8000/documents/search -Method Post -ContentType application/json -Body $body -Headers @{'Idempotency-Key'='renard-bocage-001'; 'X-Reviewer'='ecologue-local'}
Invoke-RestMethod ("http://localhost:8000" + $job.status_url)
Invoke-RestMethod ("http://localhost:8000/documents/tasks/" + $job.id + "/events")

$decision = @{relevance='accepted'; quality='accepted'; note='Pertinent pour le bocage normand'} | ConvertTo-Json
Invoke-RestMethod http://localhost:8000/documents/<id>/review -Method Post -ContentType application/json -Body $decision -Headers @{'X-Reviewer'='ecologue-local'}
```

`Idempotency-Key` sur recherche et déclenchement manuel de veille renvoie la même
tâche pour le même acteur et la même requête. Réutiliser une clé pour un autre
contenu renvoie `409`. Les décisions `relevance` et `quality` acceptent `pending`,
`accepted`, `rejected`. Les notices commencent en attente. Un rejet n'efface ni
les fichiers ni l'historique et bloque le téléchargement automatique. Une nouvelle
copie remet une qualité précédemment acceptée en attente ; une redécouverte de
métadonnées ne remplace pas une décision humaine.

Les états documentaires sont `discovered`, `imported`, `indexed`, `inaccessible`,
avec `rejected` prioritaire si l'une des deux décisions rejette le document.
`indexed` signifie texte extrait et passages stockés avec index lexical PostgreSQL,
pas index vectoriel ni validation scientifique. Un PDF vide/scanné reste `imported`
avec avertissement. Un résumé reste une métadonnée, jamais du texte intégral.
L'API conserve les noms de champs anglais pour cohérence avec le reste du projet.

`X-Reviewer` trace un utilisateur déclaré ; comme les API locales existantes, il ne
constitue pas une authentification. Conserver le déploiement sur localhost.

## Droits et sources

Les adaptateurs sont dans `sources.py` derrière l'interface `ScientificSource`.
Ajouter une source nécessite un adaptateur, son nom dans le schéma et des tests
de parsing et de politique de téléchargement.

- OpenAlex : découverte, résumé reconstruit depuis l'index fourni, DOI et métadonnées.
  Seules les locations ayant `is_oa`, un PDF et une licence reconnue peuvent fournir
  un candidat. La licence s'applique à la copie, pas à toutes les URL de la notice.
  Référence : [locations OpenAlex](https://help.openalex.org/data/locations/).
- Crossref : DOI et enrichissement de métadonnées. Ses liens TDM ne prouvent pas
  le droit d'accès et ne déclenchent aucun téléchargement automatique.
  Référence : [TDM Crossref](https://www.crossref.org/documentation/retrieve-metadata/rest-api/text-and-data-mining/).
- Europe PMC : recherche `resultType=core`, copies signalées OA avec licence explicite.
  XML intégral en premier, puis PDF OA disponibles. L'XML est contrôlé également
  pour sa déclaration de licence. Référence : [API Europe PMC](https://europepmc.org/RestfulWebService).

Politique initiale volontairement restrictive : **CC BY, CC BY-SA et CC0 seulement**
pour les téléchargements automatiques. Les licences inconnues ou autres licences
restent consultables par métadonnées, sans récupération du texte. Aucun login,
cookie, résolution de CAPTCHA, contournement de paywall ou génération de texte absent.
Un refus HTTP ou un faux PDF HTML est journalisé ; une autre copie autorisée peut
être essayée. Un téléchargement autorisé conserve URL finale, licence, preuve de
droits, taille et SHA-256. Attribution et obligations de licence restent attachées
au fichier et doivent être respectées lors de son utilisation ultérieure.

## Configuration, stockage et limites

Variables `.env` transmises par Compose :

| Variable | Défaut | Effet |
| --- | --- | --- |
| `DATA_ROOT` | `./data` | Racine persistante ; sous-dossier `documents` |
| `DOCUMENTS_CONTACT_EMAIL` | vide | Vraie adresse facultative pour User-Agent/mailto des API |
| `OPENALEX_API_KEY` | vide | Clé facultative transmise uniquement à OpenAlex, jamais écrite dans le cache |
| `DOCUMENTS_REQUEST_INTERVAL` | `1` | Secondes minimales entre appels à un même hôte |
| `DOCUMENTS_CACHE_TTL_SECONDS` | `86400` | Validité des réponses de métadonnées en cache |

Les autres réglages typés `DocumentSettings` utilisent le préfixe
`BIOSENTINELLE_DOCUMENTS_` et peuvent être transmis explicitement aux conteneurs
backend et documents : `ROOT`, `TIMEOUT_SECONDS` (25), `RETRIES` (3),
`MAX_FILE_BYTES` (32 Mio), `MAX_PDF_PAGES` (1000), `MAX_TEXT_CHARS` (4 millions),
`CHUNK_CHARS` (1600), `CHUNK_OVERLAP` (200, inférieur à la taille du passage).
Appliquer les limites de transfert identiquement au backend et au worker.

Un seul consommateur documentaire, limité à 2 CPU et 1 Gio, limite la concurrence.
Le heartbeat et l'ordonnanceur restent indépendants des téléchargements/extractions.
Extraction PDF dans un sous-processus avec délai maximal de 120 secondes.
Les erreurs mémoire/parsing n'entraînent pas le traitement de texte inventé.

Les pages PDF sont numérotées depuis 1. Le texte brut et nettoyé est conservé.
Les offsets des passages pointent dans le texte **nettoyé de leur page** ; chaque
passage possède un identifiant déterministe. Les annotations URI des PDF, les
références JATS et une détection heuristique des sections bibliographiques sont
conservées. XML/TXT/Markdown utilisent une **page logique unique**, explicitement
signalée ; il ne s'agit pas d'une pagination PDF. La langue est estimée de façon
déterministe ou `und` si le texte ne suffit pas. Pas d'OCR ni garantie de lecture
de tableaux complexes, colonnes ou références parfaitement structurées.

Stockage local interchangeable par `DocumentStorage` : `assets/<préfixe>/<sha>.<format>`,
`extracted/<sha>/<version>.json`, `cache/http`, `cache/limits`, `inbox`.
Les fichiers originaux, pages, passages et événements SQL persistent après redémarrage.
Les téléchargements et redirections refusent les destinations privées/locales et
les ports non HTTP(S) usuels. Ces contrôles applicatifs ne remplacent pas un proxy
de sortie filtrant pour un futur déploiement public.

Les réponses de métadonnées sont mises en cache avec empreinte ; les fichiers sont
réutilisés par SHA. Retries bornés avec backoff/jitter et `Retry-After`, rythme
adapté aux en-têtes Crossref. Une attente demandée supérieure à 60 secondes est
persistée et le passage différé avec erreur explicite, sans ignorer le quota.
Les requêtes sont bornées à la première page de **100 résultats maximum par source**,
sans pagination profonde. Les quotas et conditions des API peuvent évoluer :
[OpenAlex](https://help.openalex.org/api/authentication/),
[Crossref](https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication/).

## Vérifications

```sh
docker compose --profile test run --build --rm tests pytest tests/documents -o addopts=-ra
docker compose --profile test run --rm -e BIOSENTINELLE_LIVE_DOCUMENTS=1 tests pytest tests/documents/test_external_api.py -o addopts=-ra
make lint
```

La suite standard utilise fixtures PDF/JATS réelles mais synthétiques, HTTP simulé
et un schéma PostgreSQL isolé. Aucun GPU ou appel réseau externe n'est nécessaire.
Elle vérifie notamment DOI et fusions, répétition des passages, provenance,
corruption/limites HTTP, redirections privées, licences insuffisantes, pages/langue,
validation persistante, outbox, ACK après résultat durable et reprise d'import.
Le second test est explicitement facultatif : il interroge réellement les trois
sources, dépend de leur disponibilité et consomme leur quota.
