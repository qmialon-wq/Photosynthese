# Administration Symbiose — Étape 9

L’administration reprend les neuf écrans métier existants dans une composition dédiée au design Symbiose : forêt commune, surfaces sombres translucides, navigation verticale, boutons citron, actions secondaires en verre et suppressions rouges atténuées. Aucun fichier backend, worker ou modèle IA n’a été modifié. Le projet conserve Vue 3 et TypeScript, conformément à son architecture existante.

## Accès et routes

Le bouton d’engrenage ouvre « Paramètres d’affichage » et, après vérification de `/auth/me`, « Administration ». La navigation reste dans la SPA. Le rôle provient de la session serveur ; aucun rôle n’est ajouté au stockage local. Le routeur vérifie `/auth/me` à chaque navigation administrative, y compris l’accès direct par URL. Une absence de session redirige vers `/connexion` ; un compte client revient à l’Accueil.

| Rubrique | Route | Écran métier réutilisé |
| --- | --- | --- |
| Utilisateurs | `/admin/utilisateurs` | `UsersPage.vue` |
| Vue d’ensemble | `/admin` | `DashboardPage.vue` |
| Gestion des vidéos | `/admin/videos` | `VideosPage.vue` |
| Réglages d’analyse | `/admin/analyses` | `AnalysisPage.vue` |
| Datasets | `/admin/datasets` | `DatasetsPage.vue` |
| Entraînements | `/admin/training` | `TrainingPage.vue` |
| Modèles | `/admin/models` | `ModelsPage.vue` |
| Évaluation | `/admin/evaluation` | `EvaluationPage.vue` |
| Documents scientifiques | `/admin/documents` | `DocumentsPage.vue` |

La route de détail `/admin/dossiers/:id` réutilise `ParcelCorpusPage.vue` pour les dossiers réellement créés. Les anciennes entrées `/datasets`, `/training`, `/models` et `/evaluation` continuent de rediriger vers leurs routes administratives.

« Retour à l’espace observation » revient à la dernière route d’observation visitée pendant la session SPA, ou à `/` après un chargement direct. Le mode de données est conservé. `WheelNavigation.vue` est inchangé et conserve exactement six rubriques ; aucune rubrique administrative n’y a été ajoutée.

## Composition et composants communs

- `src/components/admin/AdminShell.vue` : fond commun, logo, fil d’Ariane, compte, déconnexion, sélecteur global, zone centrale défilante et confirmation des actions réelles.
- `AdminNavigation.vue` et `src/admin/navigation.ts` : neuf entrées, état actif et retour à l’observation.
- `src/styles/admin.css` : composition administrative fondée sur les variables `--sym-*` existantes. Le token commun `--sym-glass-dense` augmente l’opacité des formulaires et tableaux.
- Réemploi de `VideoCard`, `DocumentList`, `ModeSelector`, `SymIcon`, `DemoDialog`, `LoadState`, `StatusBadge`, `TaskPanel`, `MetricsPanel` et des contrôles PrimeVue existants.
- La prévisualisation des vidéos conserve un accès explicite à la configuration de leur analyse.
- Les deux espaces utilisent le même corpus canonique en démonstration et les mêmes services documentaires en réel. Aucun second stockage documentaire n’a été introduit. Les contrôleurs métier historiques restent responsables de leurs permissions et tâches.
- Sur mobile, la navigation devient un volet avec fermeture explicite, Échap, retour du focus et confinement du clavier. Ses liens sont inertes lorsqu’elle est fermée. Les tableaux défilent horizontalement dans leurs panneaux.

## Fonctions réellement raccordées

Les raccordements suivants réutilisent les services présents dans le dépôt. Ils ne signifient pas qu’un traitement réel a été exécuté pendant cette étape.

| Fonction | Services existants conservés |
| --- | --- |
| Session, rôle, déconnexion | `/auth/me`, `/auth/logout` ; cookies et CSRF existants |
| Recherche et création des comptes, changement de rôle, suppression, lien de réinitialisation, suivi des effacements | `/admin/users`, `/admin/users/:id/role`, `/admin/users/:id/reset-link`, `/admin/erasure-requests` |
| Dashboard, workers, tâches et journaux | `/console/dashboard`, `/console/workers`, `/console/tasks`, `/console/tasks/:id/logs` |
| Recherche, sélection, import segmenté et indexation locale des vidéos | `/console/videos`, `/console/uploads`, `/console/videos/local` |
| Préparation de dossiers communs et suivi groupé des imports | `/parcels/corpora`, `/parcels/import-status` et les services de détail existants |
| Configuration avancée, analyse, préparation des recadrages, consultation des résultats et artefacts | `/console/videos/:id/analyze`, `/prepare-review`, `/console/tasks/:id/artifacts/*` |
| Création, inspection, reconstruction et archive des datasets | `/review/datasets`, `/review/operations/:id`, `/review/datasets/:id/archive` |
| Choix du corpus, lancement et suivi des entraînements, arrêt, runs et métriques | `/console/training/datasets`, `/console/training`, `/console/tasks/:id/cancel`, `/training/runs` |
| Vérification des checkpoints, registre et activation explicite | `/console/models`, `/console/models/:id/activate` |
| Benchmarks et évaluation d’un modèle sur un dataset/split | `/classification/comparisons`, `/console/models/:id/evaluate` |
| Corpus, espèces, import avec droits, collecte, retrait, consultation et traduction | `/documents`, `/documents/species`, `/documents/upload`, `/documents/collect`, `/documents/remove`, `/documents/:id/pages`, `/documents/:id/translate` |

Les autorisations serveur restent appliquées par `backend/app/security.py`, installé globalement dans `backend/app/main.py`. Les protections existantes du dernier administrateur, de la propriété des ressources, des sessions et des requêtes CSRF sont conservées.

Les écritures administratives réelles demandent une confirmation avant l’envoi. Une annulation ne transmet aucune écriture. L’import d’un fichier est confirmé à son initialisation, puis ses segments et sa finalisation partagent cette autorisation ; elle est invalidée à tout changement de mode, compte ou rôle. Le POST de consultation `/parcels/import-status` reste une lecture sans confirmations répétitives. Une opération déjà transmise reste gérée par le backend et se consulte dans son suivi.

## Démonstration et indisponibilités

`src/admin/demo-provider.ts` adapte localement les contrats des pages existantes. Il n’effectue aucun `fetch` ni stockage persistant. Les comptes utilisent des adresses `@example.test`. Les modifications de ces comptes n’accordent aucun droit et ne touchent jamais aux sessions réelles.

Les vidéos, observations, dossiers et documents proviennent du scénario commun. Les imports simulent l’ajout d’un nom de fichier ; aucun média ou document authentique n’est analysé. Les tâches avancent uniquement lors des consultations locales et annoncent leur caractère simulé. L’enregistrement d’un checkpoint crée un candidat inactif ; l’activation demande une action distincte.

Les versions de datasets constituent des instantanés immuables des observations validées du scénario, avec exclusions et séparation par groupes vidéo. Une modification ultérieure des observations ne modifie pas une version créée. La disponibilité d’un dataset pour l’entraînement exige des exemples dans train et validation.

Les matrices et scores de démonstration sont des exemples fixes sur deux classes, identifiés par le mode et les noms des modèles. Ils ne mesurent aucun modèle réel. Les checkpoints, empreintes et journaux sont également fictifs. Les ZIP, vidéos annotées et exports de métriques ne sont pas proposés comme de véritables artefacts en démonstration. Les aperçus fixes sont annoncés ; le petit fichier vidéo local existant reste le seul aperçu réellement lisible quand la source le prévoit.

En réel, les pages affichent exclusivement les réponses des services. Les erreurs et états vides restent visibles sans données fictives de remplacement. Un endpoint absent en démonstration échoue explicitement au lieu de basculer vers le réseau. Un changement de mode remonte la page actuelle et efface ses paramètres de sélection pour empêcher l’envoi d’identifiants fictifs aux API réelles. Les réponses tardives d’une ancienne source sont ignorées, y compris une ancienne réponse 401.

Le mode choisi est mémorisé par le sélecteur global. Les mutations de démonstration restent en mémoire et sont réinitialisées lors d’un rechargement, d’un changement de mode ou de session.

## Comparaison et captures

La [galerie finale](../output/symbiose/etape-9/index.html) présente les neuf pages à 1600 × 900 et les contrôles complémentaires. Les anciennes captures fournies ont servi à vérifier les sections, champs et actions : comptes/création/effacements ; workers/indicateurs/activité ; imports/filtres/sélection ; analyses et réglages ; versions de datasets ; paramètres et historique des entraînements ; registre/activation ; benchmarks/évaluation ; corpus/avancement documentaire.

Leur présentation a été entièrement intégrée aux surfaces, couleurs, arrondis et contrôles Symbiose. Les longues pages défilent dans la zone centrale ; une capture du premier écran ne représente donc pas toutes leurs sections. Les captures sont produites avec une session serveur simulée dans Playwright, jamais avec de vraies informations personnelles.

## Validation

- Compilation de production Vite et contrôle TypeScript réussis.
- 68 tests unitaires réussis dans 14 fichiers, dont 11 contrôles des données et de la politique administrative.
- Les 22 parcours administratifs et les contrôles Axe des neuf pages ont réussi, avec vérification complémentaire des résultats d’évaluation. Le recontrôle final inclut aussi le passage de l’aperçu vidéo à la configuration de son analyse ; rapport : `output/symbiose/etape-9/tests-admin-final.json`.
- Le passage complet des 81 scénarios sélectionnés a réussi, sans échec, scénario ignoré ni reprise. Le rapport est consigné dans `output/symbiose/etape-9/tests-navigateur.json`.
- La roue est inchangée ; les contrôles de géométrie portent sur 1920 × 1080, 1600 × 900, 1440 × 900, 1280 × 800 et 390 × 844. L’administration est également contrôlée à 1600, 1280 et 390 pixels de large.
- La galerie contient neuf captures à 1600 × 900 et six vues complémentaires. Les images et leurs dimensions ont été vérifiées.
- Aucun fichier backend, worker ou service partagé n’a été modifié.

```powershell
cd frontend
npm run dev -- --port 4173
npm run build
npm test
npx playwright test tests/e2e/admin-design.spec.ts
```

Les vérifications des services authentifiés utilisent des réponses API contrôlées. Aucune session privée disponible dans le navigateur de test, aucun entraînement GPU, aucune modification de compte réel ni collecte documentaire réelle n’a été exécuté. Chromium est le navigateur utilisé pour ces contrôles. Les écritures métier et les workers gardent leur validation opérationnelle dans l’environnement authentifié habituel.
