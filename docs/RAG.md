# RAG BioSentinelle — étape 1, sans génération LLM

Ce module recherche les passages des publications validées et produit un **dossier
de preuves**, exportable en JSON ou Markdown. Il ne prétend pas encore interpréter
les conclusions des articles ni générer un conseil écologique spécifique. Les
champs `observed_facts`, `publication_evidence` et `inferred_recommendations` sont
séparés ; ce dernier reste vide dans cette étape. Sans source pertinente, le statut
est `no_sources`, la recommandation `abstained` et le refus est explicite.

## Démarrage

Depuis la racine, avec Docker Compose (aucun GPU ni LLM requis) :

```sh
make rag-up
make rag-prepare
make rag-index
make rag-search ARGS='--question "Préserver les haies pour les renards" --species renards'
make rag-report ARGS='--question "Quels effets des routes sur les renards ?" --species renards'
```

Toutes ces opérations retournent immédiatement un identifiant de tâche. Le worker
documentaire CPU les exécute séquentiellement via Redis Streams et son outbox SQL.
Les traductions et les collectes déjà en cours peuvent donc retarder leur exécution.

```sh
make rag-status ARGS='<task-id>'
make rag-result ARGS='<run-id>'
```

`rag-status` donne, une fois terminé, le `run_id`. La préparation télécharge une
seule fois environ **136 Mo**, uniquement dans `data/models/rag`. Aucun
téléchargement ni chargement n'a lieu à l'import ou au démarrage. L'indexation et la
recherche hybride échouent explicitement si les fichiers manquent ou sont corrompus.
Le mode `--mode lexical` fonctionne sans télécharger ni charger le modèle.

## Sources éligibles

Un document doit avoir un texte extrait, être `indexed`, avoir pertinence **et**
qualité `accepted`, et une association d'espèce activée et non retirée. Une simple
collecte, un téléchargement ou une traduction ne constitue pas une validation.
Les références bibliographiques identifiées sont exclues du retrieval.

L'API existante permet de valider et ajouter une source (sans commentaire) :

```http
PUT /documents/<document-id>/species/renards
Content-Type: application/json
X-Reviewer: ecologue

{"enabled": true}
```

Ne pas valider automatiquement l'ensemble du corpus : ce module ne contourne pas
la décision de pertinence documentaire. Après une nouvelle validation, relancer
`make rag-index` ; les fragments inchangés sont réutilisés. Les corrections de
texte et changements de modèle ont des versions/empreintes distinctes.

Un retrait ou rejet est appliqué à chaque recherche, même si ses embeddings
existent encore. Les rapports déjà produits restent des instantanés historiques
datés ; ils ne constituent pas une nouvelle recherche sur le corpus actuel.

## API asynchrone

La documentation interactive est disponible sur `http://localhost:8000/docs`.

| Endpoint | Usage |
| --- | --- |
| `POST /rag/prepare` | Préparation explicite du modèle vérifié |
| `POST /rag/index` | `{"document_ids":[]}` ; tous les documents éligibles par défaut |
| `POST /rag/search` | Recherche documentaire |
| `POST /rag/recommendations` | Rapport extractif, sans recommandation générée |
| `POST /rag/evaluate` | Évaluation sur questions et fragments de référence annotés |
| `GET /documents/tasks/{id}` | Progression, erreurs et lien du résultat |
| `GET /documents/tasks/{id}/events` | Journal du passage |
| `GET /rag/runs/{id}` | Résultat durable SQL |
| `GET /rag/runs/{id}/export?format=json` | Export complet reproductible |
| `GET /rag/runs/{id}/export?format=markdown` | Rapport lisible avec extraits et sources |

Exemple de requête pour `/rag/search` ou `/rag/recommendations` :

```json
{
  "question": "Quels effets de l'éclairage nocturne sur les renards ?",
  "mode": "hybrid",
  "limit": 8,
  "rerank": false,
  "filters": {
    "species": ["renards"],
    "habitat": "bocage",
    "territory": "Normandie",
    "sources": ["openalex", "europepmc", "manual"],
    "published_after": "2010-01-01",
    "published_before": "2026-10-23"
  }
}
```

Tous les filtres sont facultatifs. Les territoires et habitats sont des **étiquettes
documentaires explicites**, pas la localisation d'un piège ni un mot déduit d'une
requête de collecte. Leurs valeurs doivent correspondre exactement aux annotations.
Les bornes temporelles concernent les publications et sont inclusives ; les dates
partielles (année seule) sont exclues lorsqu'une borne précise est demandée.

Pour annoter ces étiquettes, `PUT /rag/documents/{id}/context` accepte
`{"habitats":["bocage"],"territories":["Normandie"],"provenance":"Lecture de la section Study area"}`.
Chaque correction est journalisée. L'absence d'une métadonnée ne vaut jamais une
correspondance au filtre.

## Observations, TAXREF et contexte territorial

Le rapport accepte aussi `"video_ids":["<review-video-id>"]`. Seules les révisions
**courantes** `validated` ou `corrected` sont reprises, avec le label humain,
l'auteur, la date, la vidéo et l'instant de l'image. Le nom de fichier et les
prédictions automatiques ne deviennent jamais des faits. Le score initial est
conservé à titre de provenance ; une correction humaine reste valide même si la
prédiction d'origine avait une faible confiance. Ces annotations ne mesurent ni
l'abondance ni le nombre d'individus distincts.

`PUT /rag/videos/{id}/context` ajoute une date avec fuseau, latitude/longitude,
territoire, habitat et une `provenance` obligatoire. L'historique est conservé.
Ces informations restent distinctes des lieux étudiés dans les publications.

`PUT /rag/taxonomy/renards` accepte `cd_nom`, `taxref_version`, `scientific_name`
et `source_url`. Les identifiants sont fournis explicitement et traçables : aucun
CD_NOM n'est inventé. Cette étape n'inclut ni import automatique TAXREF, ni connecteur
de données territoriales, ni validation distante des identifiants fournis.

## Embeddings et recherche

L'encodeur par défaut est [multilingual-e5-small](https://huggingface.co/intfloat/multilingual-e5-small),
export [ONNX quantifié Xenova](https://huggingface.co/Xenova/multilingual-e5-small),
révision et SHA256 de chaque fichier épinglés dans `shared/rag/model.json`.
L'inférence est CPU via ONNX Runtime, 384 dimensions, préfixes `query:`/`passage:`,
mean pooling et normalisation L2. Les textes longs sont segmentés, sans suppression
silencieuse de leur fin. Les embeddings et leur manifeste restent versionnés en SQL.
Les textes originaux restent la référence ; les traductions d'affichage ne les remplacent pas.

PostgreSQL combine le classement lexical `tsvector` (GIN existant) et les distances
cosinus `pgvector` par Reciprocal Rank Fusion. La recherche vectorielle est **exacte**,
adaptée au corpus local, afin de conserver des dimensions configurables et des
filtres fiables ; aucun index approximatif HNSW n'est ajouté à ce stade.
Les fragments identiques sont dédupliqués à la sortie ; les publications restent
dédupliquées par le service documentaire DOI/identifiants et empreinte de fichier.

`RAG_MIN_SIMILARITY=0.80` borne les candidats hybrides, y compris les candidats
lexicaux. C'est un seuil de retrieval configurable à calibrer, pas une probabilité
de véracité. `rerank=true` active un reclassement déterministe par couverture
lexicale, **pas** un modèle cross-encoder. Ce reclassement peut être peu utile pour
une question française et des textes anglais.

`RAG_THREADS=2` borne les threads CPU ; le worker documentaire dispose de 2 Gio de
RAM et ne réserve aucune VRAM. `RAG_MODEL_MANIFEST` peut désigner un autre manifeste
local au même format pour un encodeur XLM-R ONNX compatible (mean/L2), avec révision,
dimensions, préfixes et empreintes exacts. Après modification, redémarrer le worker,
préparer et réindexer. Aucun code distant ni fichier pickle n'est exécuté.

## Évaluation

```json
{"cases":[{"search":{"question":"hedgerow fox","mode":"lexical","limit":5},
            "relevant_chunks":["<chunk-id-validé>"]}]}
```

Envoyer ce JSON à `/rag/evaluate` ou le placer sous
`data/documents/inbox/rag-evaluation.json`, puis :

```sh
make rag-evaluate ARGS='--file /storage/documents/inbox/rag-evaluation.json'
docker compose --profile test run --rm tests pytest tests/test_rag_contracts.py
docker compose --profile test run --rm tests pytest tests/documents -m integration
```

Métriques : recall@k, precision@k, MRR, nDCG, empreinte du jeu d'évaluation et fidélité
des citations/extraits. Cette dernière vérifie la correspondance exacte aux passages
réellement utilisés ; elle **ne mesure pas** l'entailment scientifique. Pas de score
de pertinence annoncé sur un corpus réel sans annotations de référence.

Test facultatif avec le vrai encodeur préparé, sans GPU :

```sh
docker compose --profile test run --rm -v ./data/models:/storage/models:ro tests pytest tests/documents/test_rag.py -m real_model
```

La seconde étape ajoutera un générateur interchangeable (distant/Ollama), désactivé
par défaut, avec contrôle des citations et évaluation de l'appui des affirmations.
Aucun générateur LLM ni service Ollama n'est lancé dans cette première étape.
