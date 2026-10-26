# Parcelle, vidéo et dossier biodiversité

Le parcours client part de la vidéothèque : importer plusieurs vidéos ou sélectionner
les vidéos déjà présentes d'une même parcelle, puis cliquer sur **Préparer un dossier**.
Le groupe accepte de 1 à 1 000 fichiers, dont le corpus de base de 342 vidéos.
Les fichiers physiquement identiques sont dédupliqués par SHA256, même s'ils ont des
identifiants d'import différents.

Une seule page demande **surface en m²**, **type de parcelle**, **projet souhaité**
pour tout le groupe. La commune et les précisions sont facultatives. Un bouton
**Analyser les vidéos et préparer mon dossier** lance le parcours complet.

Les analyses déjà réussies sont réutilisées ; les analyses actives restent suivies
et les autres vidéos sont soumises à la file vision existante. La réservation GPU
unique est conservée. Une vidéo en échec ou annulée bloque explicitement le dossier :
aucun fichier n'est retiré silencieusement. Une relance réutilise les succès et
resoumet les vidéos en erreur. Chaque dossier fige ses vidéos, leurs analyses et la
révision du formulaire. Le modèle actif est enregistré dans les nouvelles tâches
d'analyse ; sans classificateur actif, elles utilisent la détection seule.

La navigation **Mes dossiers** (`/parcelles`) permet de retrouver les groupes et
leur avancement après fermeture ou rechargement du navigateur. L'import individuel
et les anciens dossiers attachés à une analyse restent accessibles sur la page
d'analyse ; ils ne sont pas migrés ni supprimés.

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
le worker vision : `make documents-up`. La rédaction locale de quatre pages se
prépare avec le service Ollama et le modèle décrits dans [RAG.md](RAG.md).
Elle examine les publications téléchargées et liées aux espèces, sans utiliser
un top-k de passages. Les candidats non validés sont identifiés dans l'audit ;
les documents retirés ou rejetés sont exclus. Les fichiers sans texte extrait
sont signalés. Le mode extractif reste accessible avec `RAG_GENERATION_ENABLED=false`.

## Ce que reçoit l'utilisateur

Après toutes les analyses, la page du groupe propose chaque vidéo annotée et un bouton
**Télécharger mon dossier commun (.txt)**. Le fichier UTF-8 est organisé ainsi :

1. Parcelle et projet.
2. Résultats du corpus, espèces confirmées et hypothèses automatiques.
3. Pistes sur végétation, continuités, éclairage, perméabilité, eau et calendrier.
4. Part de terrain vert : ce qui peut ou ne peut pas être chiffré.
5. Questions de conception selon le terrain et l'activité, prochaines étapes.
6. Sources réellement utilisées, DOI, pages, passages, licences et empreintes.
7. Liens vers toutes les vidéos annotées, analyses et empreintes des rapports.

Les espèces sont réunies sans additionner les passages comme des individus.
Le score d'une hypothèse agrégée est le maximum des scores des images retenues,
pas une probabilité de présence calculée sur le corpus. Les résultats par vidéo,
les références des annotations humaines et les fichiers originaux restent traçables.

Avec la rédaction locale activée, le dossier principal contient quatre pages A4 :
diagnostic et implantation, aménagements par espèce, mise en œuvre et chantier,
puis priorités et suivi. L'interface permet d'ouvrir ces pages pour impression ou
enregistrement en PDF. L'export TXT/JSON ajoute les fiches de mise en œuvre et
l'annexe complète des articles examinés, avec constats, limites, pages et citations.
Les anciens dossiers doivent être actualisés pour utiliser cette rédaction.

En mode extractif, les pistes sont proposées par un moteur de règles conservateur :
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
| `POST /parcels/corpora` | Créer un groupe avec `video_ids` ; déduplication par empreinte |
| `GET /parcels/corpora` | Retrouver les groupes créés |
| `GET /parcels/corpora/{id}` | Formulaire, vidéos, avancement et dossier commun |
| `PUT /parcels/corpora/{id}/profile` | Enregistrer le formulaire commun avec `expected_revision` |
| `POST /parcels/corpora/{id}/dossiers` | Réutiliser/soumettre les analyses et préparer un dossier |
| `POST /parcels/import-status` | État d'un lot d'imports en une requête, avec `task_ids` |
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
npm run test:e2e -- tests/e2e/parcel.spec.ts tests/e2e/corpus.spec.ts
```

Fixtures synthétiques uniquement dans les tests : aucun modèle simulé ni document
scientifique fictif n'est ajouté au corpus utilisateur.
