# RAG BioSentinelle — recherche et recommandations territoriales

Le moteur propose une recherche de passages validés et une **synthèse territoriale
locale** pour les dossiers de parcelle. La synthèse examine tous les textes
extractibles des documents associés aux espèces, puis rédige quatre pages de
recommandations adaptées au formulaire du projet. Les observations confirmées,
hypothèses automatiques, résultats des études et propositions de conception restent
distincts. Sans constat pertinent, aucune recommandation spécifique n'est inventée.

## Dossier territorial de quatre pages

```sh
docker compose --profile rag-generation up -d ollama
docker compose exec -T ollama ollama pull qwen3:4b-instruct-2507-q4_K_M
docker compose up -d --build --no-deps backend documents frontend
```

Le modèle est téléchargé explicitement, puis exécuté localement via Ollama sur CPU.
L'accélération NVIDIA est disponible avec
`docker compose -f docker-compose.yml -f docker-compose.rag-gpu.yml --profile rag-generation up -d --no-deps ollama documents`.
Elle utilise le verrou `/storage/results/.vision-gpu.lock`, commun avec la vision,
et décharge le modèle avant de le libérer. Si la vision détient déjà le verrou,
le dossier peut être relancé après son traitement, en réutilisant les notes en cache.
Les textes ne sont pas transmis à un fournisseur distant. Compose active la
rédaction avec `RAG_GENERATION_ENABLED=true` ; `false` conserve le mode extractif.
`RAG_GENERATOR_URL`, `RAG_GENERATOR_MODEL` et `RAG_GENERATOR_TIMEOUT` configurent
le service. Le modèle n'est chargé que pendant une génération.

Actualiser un dossier dans **Mes dossiers** réutilise les analyses vidéo réussies.
Les anciens dossiers restent des instantanés historiques. Les quatre pages sont :
diagnostic et implantation, aménagements pour les espèces, mise en œuvre du projet,
puis priorités et suivi. Chaque fiche précise action, localisation, justification,
conditions, priorité, indicateur de suivi et références.

La synthèse territoriale utilise les documents téléchargés, liés aux espèces et
non retirés ou rejetés, y compris les candidats encore en attente de validation.
Leur statut reste inchangé et apparaît dans l'audit. Ce périmètre est distinct de
la recherche hybride ci-dessous, qui demeure limitée aux sources validées.
Aucune espèce identifiée ne conduit à lire arbitrairement le corpus des autres.

`RAG_READING_MODE=balanced` est le mode par défaut. Tous les passages hors
bibliographies sont parcourus par une sélection textuelle locale sans modèle.
Elle conserve au plus deux extraits exacts par article (450 caractères chacun),
avec priorité aux thèmes d'aménagement, préconisations et limites ou effets
défavorables. Tous les documents restent dans l'audit, y compris ceux sans extrait
retenu. Les indices de rôle sont heuristiques, pas des résultats scientifiques.
Le modèle croise les extraits en lots bornés, puis rédige les recommandations.
Ce filtrage peut manquer des résultats implicites ou leur contexte : sa qualité
n'est pas équivalente à une lecture scientifique intégrale validée.

`RAG_READING_MODE=exhaustive` conserve l'ancien parcours : chaque lot est lu par
le modèle, qui sélectionne des extraits par identifiant et indice. Ses notes sont
mises en cache par version, modèle et texte et réutilisées entre projets.
Ce mode peut demander plusieurs jours sur un GPU de 4 Go pour plusieurs centaines
d'articles. Le mode équilibré vise une à deux heures pour le corpus courant,
sans garantie de délai sur tout matériel ou volume ; les contrôles et reprises
peuvent allonger la rédaction. Les réponses de rédaction sont mises en cache dans
les deux modes. Le modèle, les contrôles de citations et les quatre pages restent
identiques ; les lots intermédiaires sont limités à trois propositions concises.
Avant la consolidation, une sélection bornée des propositions déjà contrôlées
favorise la diversité des thèmes et des sources (10 propositions et 8 000 caractères
au maximum). Cela évite de multiplier les appels de réduction. Un lot encore
invalide après correction ne contribue aucune proposition : son rejet et son motif
restent dans `coverage.batches_rejected`, avec avertissement dans l'interface.
Les scores du classificateur ne sont pas transmis au rédacteur pour éviter de les
confondre avec une mesure écologique.

Une référence inconnue, une citation inventée, un contexte trop long ou une sortie
tronquée empêche la publication.
Une réduction hiérarchique synthétise ensuite les constats de tous les documents.
Un document examiné peut être écarté des recommandations pour manque de pertinence ;
il reste dans le registre, avec ses passages parcourus et le mode de sélection.
Les fichiers sans texte extrait restent signalés comme non analysables.

`territorial_report.coverage` expose documents présents/lus, passages lus,
documents en attente de validation et fichiers non analysables. `ledger` conserve
les constats, limites, extraits exacts, pages et empreintes. Les citations vérifiées
ne constituent pas une validation automatique de l'interprétation scientifique.
Les simples études ou inventaires ne sont pas présentés comme des mesures
d'aménagement. Des contrôles rejettent les interventions sans appui thématique et
les prescriptions chiffrées non définies localement. Les valeurs des paragraphes
doivent figurer dans les extraits cités, avec leurs unités, ou dans le formulaire.
Les durées de suivi inventées sont remplacées par un protocole méthodologique
qualitatif dont la durée reste à définir après le diagnostic du site.
La lecture exhaustive est plus lente qu'une recherche de passages ; les événements
de tâche montrent l'avancement document par document et page par page.

L'export de parcelle `?format=html` produit quatre pages A4 imprimables en PDF depuis
le navigateur. TXT/Markdown et JSON ajoutent les fiches et l'annexe complète du
corpus, qui peut dépasser quatre pages. La densité typographique du rapport principal
s'adapte aux pages les plus détaillées ; des bornes de validation empêchent une
sortie vide ou démesurée.
Le corpus est figé au démarrage. Les ajouts ultérieurs sont comptés pour proposer
une actualisation ; un retrait ou rejet pendant la rédaction empêche sa publication.

`POST /rag/recommendations` active aussi la synthèse complète lorsque le corps
contient `profile` (mêmes champs que le formulaire de parcelle) et les espèces
cibles dans `filters.species`. Sans `profile`, le rapport extractif reste disponible.
Dans le mode territorial, le périmètre est l'ensemble du corpus lié aux espèces :
les filtres de recherche de passages et `limit` ne le tronquent pas.

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
Une traduction ou collecte déjà en cours peut retarder leur exécution. Les dossiers
et rapports sont prioritaires sur les traductions en attente, pour éviter qu'une
collecte volumineuse bloque la préparation du dossier derrière des centaines de fichiers.

```sh
make rag-status ARGS='<task-id>'
make rag-result ARGS='<run-id>'
```

`rag-status` donne, une fois terminé, le `run_id`. La préparation télécharge une
seule fois environ **136 Mo**, uniquement dans `data/models/rag`. Aucun
téléchargement ni chargement n'a lieu à l'import ou au démarrage. L'indexation et la
recherche hybride échouent explicitement si les fichiers manquent ou sont corrompus.
Le mode `--mode lexical` fonctionne sans télécharger ni charger le modèle.

## Sources éligibles à la recherche de passages

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
| `POST /rag/recommendations` | Synthèse territoriale avec `profile`, sinon rapport extractif |
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

La recherche et les rapports extractifs restent utilisables sans service Ollama.
La rédaction territoriale nécessite le modèle local préparé et le profil de parcelle.
