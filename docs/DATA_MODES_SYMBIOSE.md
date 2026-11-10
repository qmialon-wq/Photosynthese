# Symbiose — deux modes de données

## Utilisation

Le choix de la source se trouve dans **Paramètres → Paramètres d’affichage → Source de données**. La première visite anonyme démarre en démonstration ; une connexion ou inscription réussie active les données réelles. Le choix est conservé dans `localStorage`, sous `symbiose:data-mode:v1` ; aucune donnée métier ni aucun jeton n’est enregistré avec cette préférence.

Le changement de mode conserve l’URL et la rubrique active. Il remplace l’état de la page : sélections, filtres, pagination, modales et simulations en cours sont réinitialisés. La roue reste montée et ne tourne pas lors du basculement. Son composant n’est pas modifié.

La page Connexion conserve son interface et son authentification. Elle n’affiche pas le sélecteur et ne déclenche aucune lecture métier liée aux modes. Les paramètres du compte et la déconnexion restent des opérations d’authentification réelles, distinctes des simulations.

## Inventaire effectué avant l’implémentation

- Frontend existant : **Vue 3, TypeScript, Vue Router**, composants Symbiose et six pages de présentation. La stack n’est pas remplacée par React.
- Données de présentation : `*-preview.ts`, jeux auparavant indépendants, compteurs incohérents entre rubriques, simulations locales d’analyse, de validation et de récupération documentaire.
- Média réellement présent dans les assets : `squirrel-local.mp4`. Sa lecture est réelle, ses résultats de détection de démonstration restent fictifs. Les autres aperçus photographiques ne sont pas des vidéos enregistrées dans le backend.
- Backend existant : FastAPI, PostgreSQL, stockage local, Redis et workers de traitement ; API de session, console vidéo, observations, corpus de parcelles, analyses et documents. Aucune de ces couches n’a été remplacée ou développée dans cette étape.
- Authentification existante : cookie de session, jeton CSRF pour les écritures et contrôle des permissions/propriétaires côté serveur.
- Vérification locale : `/health` répond **200** et `/auth/me` sans cookie répond **401**. Aucun compte ni aucune session n’a été créé pour contourner cette protection. Les données privées réellement enregistrées ne peuvent donc pas être inventoriées depuis cette session de développement non authentifiée.

## Architecture

`main.ts` fournit un contexte Vue typé à l’application. `data/data-mode.ts` expose `mode`, `setMode`, `isDemo`, `isReal`, les collections, leurs états, les capacités disponibles et une identité de source comprenant le compte connecté. Les pages consomment `useCollection()` et les composants visuels reçoivent les mêmes contrats dans les deux modes.

`data/contracts.ts` centralise les modèles de vidéos, dossiers, observations, espèces, médias d’analyse, détections, documents, statistiques et recommandations. Les anciennes signatures de types de démonstration restent des alias de ces contrats pour préserver les imports existants.

Chaque collection expose `loading`, `success`, `empty`, `error` ou `unconnected`. Les valeurs absentes restent nulles ou non renseignées et sont présentées comme « — », « Non disponible » ou un état explicite. `SourceState` est le composant commun d’affichage et de nouvelle tentative.

`DemoDataProvider` construit le scénario local. `RealDataProvider` effectue uniquement des requêtes **GET** à travers le client API existant, avec les cookies et permissions habituels. Il vérifie d’abord `/auth/me`. Une session absente ou un accès refusé ne provoque aucun repli vers des exemples fictifs.

La lecture seule de cet adaptateur n’interdit pas les actions métier : la vidéothèque cliente envoie les imports réels et crée les dossiers avec le même client API, puis les formulaires enregistrent profils et coordonnées. `capabilities.write` est disponible pour tout compte connecté en mode réel, administrateur ou client. Les contrôles de propriété et CSRF restent appliqués par le serveur.

Les snapshots sont remplacés au changement de mode et de compte. Les requêtes et rapports en cours sont annulés via `AbortController` ; une génération protège aussi contre les réponses tardives, même si un transport ne respecte pas l’annulation. Il n’y a pas de cache persistant de données métier. Les mutations locales sont refusées par le contexte hors démonstration.

## Scénario de démonstration

- 248 vidéos fictives et 12 dossiers reliés par identifiants ; les compteurs de chaque dossier sont calculés depuis ses vidéos.
- 8 observations, dont 2 initialement validées, liées aux mêmes médias et noms de fichier que la Vidéothèque et les Analyses.
- 3 analyses illustratives, avec durées et identifiants de vidéo partagés.
- 8 documents explicitement fictifs, répartis par espèce ; le corpus Renard est initialement vide pour présenter cet état.
- Accueil calculé depuis ces collections : 12 territoires, 8 observations disponibles, 2 espèces validées et 4 recommandations de démonstration. Le diagnostic 78/100 et les recommandations restent des illustrations, jamais des mesures réelles.

Les simulations d’analyse, de validation, de retrait et de récupération restent locales. Leurs changements de collection sont partagés entre rubriques pendant la session de démonstration. Un rechargement ou un nouveau basculement vers la démonstration recharge le scénario stable ; seul le choix du mode est persistant.

## Sources réelles raccordées

| Source | Points d’accès existants | Consultation proposée |
| --- | --- | --- |
| Session | `GET /auth/me` | Vérification préalable de la session, sans création de compte |
| Vidéos | `GET /console/videos`, `GET /console/videos/{id}/file` | Liste, recherche, filtres, pagination locale et lecture du fichier autorisé |
| Observations | `GET /review/samples`, `GET /review/samples/{id}/images/original` | Observations enregistrées, statut, espèce, qualité, protection et image réelle |
| Espèces | `GET /review/species` | Catalogue de la source authentifiée |
| Dossiers | `GET /parcels/corpora`, `GET /parcels/corpora/{id}` | Groupes enregistrés, profil et vidéos associées |
| Analyses | `GET /console/tasks?kind=analysis`, `GET /console/tasks/{id}/artifacts/video`, `GET /console/tasks/{id}/artifacts/report` | États réels, vidéo annotée disponible et détections horodatées du rapport |
| Documents | `GET /documents?stored_only=true` | Documents effectivement stockés, métadonnées et lien original lorsque fourni |
| Statistiques | Calcul local sur les réponses précédentes | Volumes accessibles et espèces humainement validées ; aucune mesure écologique synthétique inventée |

Les listes paginées de vidéos, observations et documents sont parcourues avant de calculer un total. Les limites existantes de 100 dossiers et 200 analyses sont signalées si elles sont atteintes ; un total incomplet n’est pas présenté comme exhaustif. Une collection trop volumineuse pour la borne de lecture affiche une erreur explicite.

Les captures `api-test-*` illustrent les adaptateurs avec des réponses API interceptées pour les tests. Elles ne représentent pas les données privées de l’utilisateur. La réponse 401 du serveur local sans session a été vérifiée séparément.

## Fonctionnalités restant hors connexion dans les six écrans

- L’import de vidéos, la création de dossiers, l’enregistrement de brouillons et la modification du formulaire sont raccordés dans l’espace client. La génération du dossier réutilise les analyses réussies et programme celles qui manquent. Les autres commandes de simulation (analyse isolée depuis l’écran de présentation, validation en lot et collecte documentaire) conservent leurs limitations propres.
- Le diagnostic écologique global n’est pas calculé ; il est masqué en mode réel. L’accueil reprend les recommandations des dossiers terminés avec leurs liens.
- Suivi des récupérations documentaires dans le panneau Avancement : explicitement non connecté dans cet écran.
- Les vignettes réelles utilisent le poster disponible ou une image extraite à mi-durée ; un média illisible conserve un état neutre. Les paysages de démonstration ne remplacent pas des données réelles.
- L’administration authentifiée possède un `AdminShell` et un adaptateur local de démonstration. Ses actions fictives restent en mémoire ; ses actions réelles réutilisent les services existants après confirmation. Le parcours client reste directement accessible sans passer par l’administration. Voir [ADMIN_SYMBIOSE.md](ADMIN_SYMBIOSE.md).

## Vérification

Depuis `frontend/` :

```powershell
npm run dev -- --port 4173
npm test
npm run build
npx playwright test tests/e2e/data-modes.spec.ts
```

Les tests de contrat couvrent la cohérence des identifiants et compteurs, la pagination API, les sources inaccessibles, les permissions, les réponses malformées, les changements de compte, la persistance et les réponses tardives. Les tests navigateur couvrent les scénarios A à E, les simulations, les écritures désactivées, le clavier, le mobile, les erreurs et les captures des douze vues à 1600 × 900.

## Résultats finaux

- **57 tests unitaires réussis**, répartis dans 13 fichiers, dont 11 tests de contrats et de séparation des modes.
- **Compilation Vite et contrôle TypeScript réussis** ; un contrôle TypeScript final est également passé après les derniers ajustements.
- **55 scénarios navigateur distincts validés**. Le passage complet a réussi 54 scénarios ; un contrôle du plein écran mesurait les deux rectangles pendant un redimensionnement. Il a été corrigé pour les mesurer atomiquement et attendre ResizeObserver, en conservant la tolérance de 0,005. Le recontrôle du scénario est passé, puis le dernier passage des **14 scénarios Analyse et Modes a entièrement réussi**.
- Les neuf nouveaux scénarios couvrent A à E, les réponses tardives, l’absence de session, les états vides, les erreurs 403/503 et la lecture seule. Toutes les requêtes métier interceptées en mode réel sont des GET ; aucune requête métier n’est émise en démonstration.
- Les contrôles existants de géométrie passent aux cinq résolutions : 1920 × 1080, 1600 × 900, 1440 × 900, 1280 × 800 et 390 × 844. Le composant `WheelNavigation` est inchangé.
- Les analyses Axe des états testés, la navigation clavier, les filtres, les paginations, les modales et les simulations passent.
- **14 captures finales conservées** : 12 vues des six rubriques dans les deux modes, un état réel « Connexion requise » obtenu avec le serveur local et une vue mobile. La galerie charge correctement les douze captures comparatives.
- `git diff --check` réussit. Aucun fichier backend ni traitement métier n’a été modifié.

Ouvrir `output/symbiose/etape-8/index.html` pour les captures. Les résultats bruts du passage complet sont dans `tests-navigateur.json`, le contrôle d’alignement dans `test-alignement.json`, le dernier passage de 14 scénarios dans `tests-recontrole.json` et la vérification du serveur local dans `verification-locale.json`.

Les anciennes assertions de nombres et noms propres aux maquettes ont été mises à jour pour le scénario partagé. Les vérifications de comportement et de géométrie sont conservées. Le corpus local persiste désormais entre rubriques, et son contenu n’est pas écrit dans le stockage réel.

### Limites de validation

La lecture des véritables dossiers privés d’un compte n’a pas été effectuée : aucune session utilisateur n’était disponible dans le navigateur de test. Les adaptateurs authentifiés ont été vérifiés avec des réponses API contrôlées ; la protection 401 du serveur local a été vérifiée directement. Après connexion dans le navigateur habituel, le même fournisseur utilise les cookies existants et les réponses autorisées du serveur.

Les tests navigateur ont utilisé Chromium ; les modèles IA, les workers et les écritures métier n’ont pas été exécutés pour cette étape.
