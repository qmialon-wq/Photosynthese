# Validation humaine locale

Les dix classes confirmées et leurs indices sont conservés (`v3-10.1`).
Le nom du fichier donne une **suggestion provisoire**, jamais un label validé.
Une correction ne déclenche aucun entraînement.

## Démarrage

Depuis la racine du dépôt, dans PowerShell, WSL2 ou Linux :

```sh
make detector-fetch
make review-up DEVICE=cuda
# Variante sans GPU :
make review-up DEVICE=cpu
```

Les poids sont téléchargés uniquement par la première commande explicite,
avec la vérification d'intégrité existante. Les deux variantes de `review-up`
utilisent le consommateur ML unique et les migrations Alembic. Les opérations
d'import, de rendu et d'export passent dans sa file Redis ; aucune de ces
opérations longues n'est exécutée dans une requête HTTP. `docker compose up -d`
suffit pour l'API et les bases, mais n'active pas le consommateur ML : les
opérations soumises restent alors en attente.

Documentation interactive : <http://localhost:8000/docs>, rubrique `human-review`.
Les mêmes routes sont accessibles via `http://localhost:8080/api/review/...`.
Les paramètres PostgreSQL, Redis, `DATA_ROOT`, les chemins de modèles et les
variables `BIOSENTINELLE_VISION_*` existants sont réutilisés, sans nouveau secret.

## Import et revue avec PowerShell

Déposer une vidéo dans `data/datasets/inbox/chevreuil-001.mp4`, puis :

```powershell
$api = 'http://localhost:8000'
$headers = @{'X-Reviewer' = 'prenom.nom'}
$import = Invoke-RestMethod "$api/review/videos/import" -Method Post -Headers $headers -ContentType 'application/json' -Body '{"video":"chevreuil-001.mp4","group_id":"sequence-camera-A-001","split":"train","classify":false}'
Invoke-RestMethod "$api$($import.status_url)"
$samples = Invoke-RestMethod "$api/review/samples?state=pending&limit=50"
$sample = $samples[0]
```

Attendre `status=completed` avant de valider. `status=error` contient une erreur
explicite ; une extraction partielle ou illisible ne produit jamais le statut
« aucune détection ». `classify=true` active les propositions du classificateur
local configuré ; il faut alors un checkpoint compatible. Par défaut, seule
la détection MegaDetector est utilisée.

Un `group_id` rassemble les vidéos liées, par exemple une même séquence de
caméra découpée en fichiers. Tous ses exemples partagent un split immuable.
Sans groupe explicite, le SHA-256 de la vidéo sert de groupe. Sans split
explicite, une affectation déterministe par groupe et seed réserve 15 % au
test, 15 % à la validation, le reste au train. Il faut regrouper les séquences
liées dès l'import : la recherche visuelle de doublons ne remplace pas ce choix.
Une vidéo déjà connue par son contenu ne peut pas changer de groupe ou de split.

L'original est copié dans `data/datasets/imported/<sha256>/` sans modifier
l'inbox. Les frames échantillonnées et recadrages sont archivés par SHA-256 dans
`data/results/vision/review/blobs/`. Les très petits recadrages restent visibles,
avec un indicateur de qualité, au lieu d'être supprimés silencieusement.

Consulter les images :

```powershell
Invoke-WebRequest "$api/review/samples/$($sample.id)/images/original" -OutFile original.jpg
Invoke-WebRequest "$api/review/samples/$($sample.id)/images/initial_crop" -OutFile initial.jpg
```

Valider ou corriger en donnant explicitement une espèce canonique de
`GET /review/species`. Les coordonnées sont normalisées **xywh**, relatives à
l'image originale, et comprises dans l'image. Exemple :

```powershell
$decision = @{
    expected_revision = $sample.revision
    decision = 'validate'
    label = 'chevreuil'
    box = @{x=0.20; y=0.15; w=0.50; h=0.60}
    reason = 'Animal et limites vérifiés sur image originale'
    provenance = @{outil='api'; session='revue-001'}
} | ConvertTo-Json -Depth 5
$correction = Invoke-RestMethod "$api/review/samples/$($sample.id)/decisions" -Method Post -Headers $headers -ContentType 'application/json' -Body $decision
Invoke-RestMethod "$api/review/samples/$($sample.id)/history"
```

Une modification de boîte crée un rendu asynchrone identifié par
`render_operation_id`. Attendre `render_status=ready` pour exporter.
Le rendu utilise l'image originale et une recette enregistrée (marge 12 %,
JPEG 93 par défaut), en conservant le recadrage initial et les anciens rendus.
Une simple validation de label peut omettre `box` et réutilise le rendu courant.
`expected_revision` empêche l'écrasement d'une correction concurrente (HTTP 409).

États : `pending` = à revoir ; `validated` = validé ; `corrected` = corrigé ;
`rejected` = rejeté. Pour rejeter, envoyer `decision="reject"`, sans label ni
boîte. Pour reprendre une revue, utiliser `decision="reopen"`. Les deux actions
exigent la révision courante et un motif. Chaque décision ajoute une révision
datée, avec acteur, motif, provenance et référence à sa révision parente.

## Recherche et priorité

| Route | Usage |
| --- | --- |
| `GET /review/videos?status=no_detections` | Vidéos sans animal sur les frames échantillonnées |
| `GET /review/videos/{id}/imports` | Historique des imports, noms et opérateurs |
| `GET /review/samples?state=pending` | File de revue triée par priorité |
| `GET /review/samples?label=geai` | Filtre par label humain ou proposition |
| `GET /review/samples?quality=blurry` | Flou ; aussi `too_small`, `near_duplicate` |
| `GET /review/samples/{id}/images/crop?revision=1` | Ancien rendu conservé |

La priorité combine la rareté dans le **train validé uniquement** et
l'incertitude de classification (absence de prédiction comprise). Le score de
détection est conservé séparément. Les filtres prennent `limit` (1–200) et `offset`.

Les indicateurs de qualité sont des heuristiques versionnées : variance du
Laplacien < 50 pour le flou, côté < 28 pixels, dHash à distance ≤ 4 et écart
moyen de niveaux de gris ≤ 8 pour les quasi-doublons. Les valeurs et seuils sont
enregistrés. Ils signalent des exemples à examiner, sans les rejeter automatiquement.
La comparaison est exhaustive dans le worker, adaptée à ce dépôt local ; elle
devra être indexée si le volume augmente beaucoup. Elle peut avoir des faux
positifs et ne garantit pas de retrouver toutes les scènes apparentées.

`no_detections` concerne les images **échantillonnées** (24 par vidéo par défaut),
pas une garantie que toute la vidéo est vide. Le manifeste d'extraction, les
compteurs et la configuration restent consultables dans les diagnostics.

## Datasets versionnés et protection du test

```powershell
$export = Invoke-RestMethod "$api/review/datasets" -Method Post -Headers $headers -ContentType 'application/json' -Body '{"name":"biodiversite-v1","exclude_quality":["too_small"],"exclude_groups":[]}'
$operation = Invoke-RestMethod "$api$($export.status_url)"
# Après status=completed :
$version = $operation.result.dataset_id
Invoke-WebRequest "$api/review/datasets/$version/archive" -OutFile dataset.zip
Invoke-RestMethod "$api/review/datasets/$version/rebuild" -Method Post -Headers $headers
```

Le snapshot est pris **au traitement de la tâche**. Il inclut uniquement les
révisions courantes validées/corrigées dont le rendu est prêt, issues d'imports
terminés. Rejets et exemples à revoir sont exclus. Les filtres d'exclusion sont
enregistrés ; aucune exclusion de qualité n'est implicite.

Chaque version possède un identifiant de contenu SHA-256 et fige les labels,
boîtes, splits, recettes, empreintes de sources, manifeste des dix classes et
historiques des exemples inclus. L'archive contient :

- `manifest.json` : snapshot détaillé et provenance ;
- `training.json` : manifeste compatible avec le classificateur existant ;
- `classes.json` : classes et ordre ;
- `images/` et `originals/` : recadrages retenus et images sources correspondantes.

Les vidéos originales restent sur le volume datasets ; elles ne sont pas
dupliquées dans le ZIP. Après extraction, la CLI existante `train-classifier`
accepte `--storage-root <dossier extrait>` et `--manifest <dossier extrait>/training.json`,
**sur demande séparée uniquement**. Les mêmes chemins peuvent être définis par
`output_root` et `train_manifest` dans son fichier JSON de configuration.
Conserver le dossier sous `data/results/` et utiliser ses chemins `/storage/results/...`
pour qu'il soit visible dans les conteneurs.

Les ZIP utilisent un ordre, des métadonnées et des dates fixes. La reconstruction
lit le snapshot enregistré et vérifie les blobs, sans relire les labels courants.
L'empreinte de l'archive doit rester identique. Un blob manquant/corrompu ou une
incompatibilité de reconstruction provoque une erreur explicite.

Les splits ne changent jamais. Les doublons exacts/quasi identiques entre splits
bloquent l'export ; les images et recadrages du test sont protégés même s'ils ne
sont pas encore validés. On peut exclure un groupe non-test dans la sélection,
sans déplacer un exemple vers le train. Dès qu'un groupe test participe à un
snapshot, ses annotations sont gelées : les corrections et réouvertures sont
refusées, y compris par des garde-fous PostgreSQL. Aucun endpoint de dégel
n'est fourni. Les anciennes versions des autres splits restent inchangées
après une correction ultérieure.

## Persistance, erreurs et tests

PostgreSQL conserve les imports, frames, recadrages, révisions, comparaisons,
opérations et versions de datasets. L'outbox transactionnelle permet de garder
une correction et son rendu à effectuer même si Redis est indisponible ; le
worker republie au retour de Redis. Les messages interrompus sont repris et
le verrou d'opération empêche leur double exécution. Les erreurs terminales sont
consultables via `/review/operations/{uuid}`. Un import peut être soumis à nouveau ;
un rendu en erreur peut être repris par une nouvelle décision ; une archive
figée peut être reconstruite via `rebuild`.

Le worker seul a besoin d'écrire dans le volume datasets pour les copies
d'import. Le backend garde ce volume en lecture seule. Sauvegarder **ensemble**
PostgreSQL et les dossiers datasets/results : le hash détecte une altération,
mais ne remplace pas une sauvegarde. Aucun nettoyage automatique de ces blobs.

`X-Reviewer` est une identité déclarée dans cette application locale, pas une
authentification. Les ports restent liés à localhost. Une authentification et
des rôles restent nécessaires avant une ouverture multiutilisateur à distance.

```sh
make test
make review-tests
make lint
```

`review-tests` exécute les tests unitaires et les scénarios PostgreSQL avec
vidéos synthétiques et détecteur de test, sans GPU ni téléchargement. Démarrer
PostgreSQL auparavant (`docker compose up -d postgres`). Chaque scénario utilise
son propre schéma temporaire ; aucune annotation réelle n'est modifiée.
