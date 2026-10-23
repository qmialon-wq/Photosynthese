# Parcelle, vidéo et dossier biodiversité

Le parcours client part de la vidéothèque : importer une vidéo, puis remplir les
trois champs **surface en m²**, **type de parcelle**, **projet souhaité** sur la page
d'analyse. La commune et les précisions sont facultatives. Décocher « Recevoir mon
dossier biodiversité » permet de conserver une analyse vidéo seule.

Les cinq terrains proposés sont bois, pâturage, friche, terrain constructible et
terrain artificialisé. Les projets sont habitation, culture, élevage, parc/jardin
ou autre activité. Ces informations sont déclaratives : choisir « constructible »
ne constitue pas une vérification du statut du terrain.

## Lancement

À la racine, pour le parcours complet avec le worker d'inférence déjà configuré :

```sh
make inference-up DEVICE=cuda
# ou, pour une machine sans NVIDIA :
make inference-up DEVICE=cpu
```

Ouvrir `http://localhost:8080/videos`. Le modèle actif et MegaDetector restent ceux
de l'installation existante ; cette fonctionnalité ne télécharge ni n'entraîne de
modèle au démarrage. Sans classificateur actif, la détection seule reste proposée.

Pour actualiser seulement le backend, les documents et l'interface, sans relancer
le worker vision : `make documents-up`. Les embeddings RAG se préparent explicitement
avec `make rag-prepare` ; sans ce modèle, le dossier reste fonctionnel en recherche
lexicale avec cette limite signalée. Les publications doivent être téléchargées,
indexées, validées en pertinence/qualité et activées dans le corpus RAG.

## Ce que reçoit l'utilisateur

Après l'analyse, la même page propose la vidéo annotée et un bouton
**Télécharger mon dossier (.txt)**. Le fichier UTF-8 est organisé ainsi :

1. Parcelle et projet.
2. Résultats de la vidéo, espèces confirmées et hypothèses automatiques.
3. Pistes sur végétation, continuités, éclairage, perméabilité, eau et calendrier.
4. Part de terrain vert : ce qui peut ou ne peut pas être chiffré.
5. Questions de conception selon le terrain et l'activité, prochaines étapes.
6. Sources réellement utilisées, DOI, pages, passages, licences et empreintes.
7. Lien vers la vidéo annotée et versions des données.

Les pistes sont proposées par un moteur de règles conservateur, **sans LLM** :
il exige une phrase de recommandation explicite et une intervention correspondant
au thème, et écarte des négations/conditions courantes. La phrase originale est
citée. Ce filtre lexical ne prouve pas l'entailment scientifique, ne comprend pas
toutes les nuances, et ne remplace pas la lecture de la publication ni l'expertise
du site. Les suggestions restent des directions à étudier, pas un plan de travaux
dimensionné ou une garantie de maintien de toutes les activités et espèces.

La recherche multilingue prend en compte le projet, le terrain et les espèces.
La commune n'est pas assimilée au territoire d'étude d'une publication. Le moteur
ne prétend pas que les effets publiés sont déjà établis sur la parcelle.

**Aucun pourcentage de terrain vert n'est actuellement prescrit.** La surface et
une courte vidéo ne suffisent pas à le calculer ; le rapport indique qu'il doit
être déterminé après examen du site et des sources applicables. Les champs JSON
`green_space.recommended_percent` et `recommended_area_m2` restent `null`.
Sans source pertinente et explicite, le dossier explique le manque de preuves au
lieu de remplir les rubriques avec de faux conseils.

Une prédiction `species_recognized` demeure une hypothèse automatique. Les états
`species_uncertain` et `detection_unclassified` ne fournissent aucun label certain.
Seules les annotations courantes humaines `validated`/`corrected` constituent des
présences confirmées. Le lien console/revue utilise l'empreinte de la vidéo ; les
noms de fichiers ne sont jamais utilisés comme preuves.

## Persistance et reprise

Chaque modification du formulaire crée une révision immuable. Une écriture avec
une révision obsolète reçoit un conflit HTTP 409. Le lancement de l'analyse et la
demande de dossier sont enregistrés dans la même transaction SQL.

Le heartbeat du worker documentaire détecte les analyses terminées et soumet la
tâche de dossier via l'outbox Redis existante. **Fermer le navigateur ne bloque pas
la préparation.** Une analyse annulée ou en erreur donne un état explicite. Les
clics répétés réutilisent une demande active ; un échec documentaire peut être
relancé sans recalculer la vidéo.

Les collectes et traductions en cours peuvent retarder le dossier dans la file
documentaire CPU. La page indique attente, traitement, disponibilité ou erreur.
Les dossiers sont conservés dans PostgreSQL et persistent après redémarrage.

Après une correction d'espèce, revenir à l'analyse puis cliquer sur **Actualiser
mon dossier**. Le dossier antérieur conserve son instantané ; les sources retirées
ne sont pas utilisées pour une nouvelle préparation. Aucun entraînement n'est lancé.

## API

| Endpoint | Usage |
| --- | --- |
| `GET /parcels/options` | Choix canoniques du formulaire |
| `GET /parcels/videos/{video_id}?analysis_id={uuid}` | Profil et dernier dossier de cette analyse |
| `PUT /parcels/videos/{video_id}` | Enregistrer le formulaire avec `expected_revision` |
| `POST /console/videos/{video_id}/analyze` | Ajouter `parcel_revision` pour la préparation automatique |
| `POST /parcels/videos/{video_id}/dossiers` | Actualiser à partir de `analysis_id` et `profile_revision` |
| `GET /parcels/dossiers/{id}/export` | Dossier texte téléchargeable |
| `GET /parcels/dossiers/{id}/export?format=markdown` | Export Markdown |
| `GET /parcels/dossiers/{id}/export?format=json` | Instantané structuré et complet |

## Vérification

```sh
docker compose --profile test run --rm tests pytest tests/test_parcel_contracts.py tests/documents -m 'not real_model'
cd frontend
npm test
npm run test:e2e -- tests/e2e/parcel.spec.ts
```

Fixtures synthétiques uniquement dans les tests : aucun modèle simulé ni document
scientifique fictif n'est ajouté au corpus utilisateur.
