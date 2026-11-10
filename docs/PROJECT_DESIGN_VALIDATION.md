# Recette — alternatives de conception

Date : 10 novembre 2026. Branche : `feature/opendata`.

La nouvelle couche fournit douze options concrètes pour les cinq interventions. Chaque option conserve l’intervention initiale, l’enjeu potentiel, le changement au projet, les conditions, les preuves citées, les limites et le niveau de justification. Aucun service, endpoint, modèle ou changement de schéma SQL n’est ajouté.

## Résultats exécutés

| Vérification | Résultat |
|---|---|
| Suite CPU complète | **229 réussis**, 11 ignorés (torch/sklearn facultatifs), 102 désélectionnés |
| Règles de conception + règles territoriales + intégrations territoriales, premier passage | **29 réussis** |
| Conception + intégrations territoriales après renforcement des références | **24 réussis** |
| Territoire + authentification avec sessions réelles | **15 réussis** |
| Vitest | **82 réussis**, dont quatre nouveaux scénarios d’affichage des alternatives |
| TypeScript/Vite | Build réussi |
| Playwright territorial | **3 réussis**, dont scénario A/B, export, accessibilité Axe et mobile |
| Ruff complet | Réussi |
| `git diff --check` | Réussi |

Les tests unitaires ajoutés couvrent les cinq interventions et l’absence d’intervention, l’ajout/retrait/changement de codes sur un même terrain, l’invariance des options d’éclairage lorsqu’on ajoute une clôture, les couches vides/indisponibles/en erreur, l’exclusion des prédictions et les niveaux de justification. Le contrat refuse les références inventées, les références non explicitement citées, les niveaux contextualisés sans contexte pertinent, les qualifications scientifiques sans source examinée pour l’alternative précise et tout statut de validation locale ou de compensation introduit dans une option.

Les intégrations territoriales utilisent de vraies sessions de comptes propriétaires et tiers, PostgreSQL, Redis et le worker existant. Elles vérifient aussi l’export des propositions et l’immuabilité de la première analyse après changement d’interventions. Les candidats documentaires apparaissent comme sources à examiner sans promotion scientifique automatique.

## Démonstration navigateur vérifiée

1. Enregistrer un point et l’éclairage extérieur : trois options d’éclairage.
2. Ajouter une clôture, enregistrer : l’analyse précédente est signalée obsolète.
3. Relancer : six options, réparties entre éclairage et clôture, avec des changements concrets au projet.
4. Ouvrir les justifications : intervention déclarée, références générales et limites visibles.
5. Lire l’export depuis le lien proposé : les interventions figées, alternatives, changements et niveaux sont conservés.
6. Passer à une largeur mobile de 390 pixels : absence de débordement dans le composant d’alternatives.
7. Retirer l’éclairage et relancer : seules les trois options de clôture restent.

Les captures sont des **fixtures de test**, sans observation de terrain réelle ni appel IGN direct. Leurs données de conception proviennent du vrai moteur déterministe, à partir d’interventions synthétiques et de couches vides. Le fond OSM est bloqué dans le test navigateur pour la reproductibilité.

- [Comparaison éclairage + clôture, ordinateur](../output/playwright/project-adaptation-test-fixture.png)
- [Même comparaison, mobile](../output/playwright/project-adaptation-mobile-test-fixture.png)
- [Parcours propriétaire et formulaire historique conservé](../output/playwright/territorial-owner-design-test-fixture.png)

## Commandes exécutées

Depuis la racine du dépôt :

```sh
rtk proxy docker run --rm \
  -v "$PWD:/app:ro" biosentinelle-tests pytest -q

rtk proxy docker run --rm --network biosentinelle_services \
  -v "$PWD:/app:ro" -e POSTGRES_HOST=photosynthese-postgres \
  -e REDIS_URL=redis://photosynthese-redis:6379/0 \
  biosentinelle-tests pytest tests/test_design_proposals.py \
  tests/documents/test_territorial.py -m 'not gpu' -q

rtk proxy docker run --rm --network biosentinelle_services \
  -v "$PWD:/app:ro" -e POSTGRES_HOST=photosynthese-postgres \
  -e REDIS_URL=redis://photosynthese-redis:6379/0 \
  biosentinelle-tests pytest tests/documents/test_territorial.py \
  tests/documents/test_authentication.py -m integration -q

rtk proxy docker run --rm -v "$PWD:/app:ro" biosentinelle-tests \
  ruff check backend shared workers tests infra/init_storage.py

git diff --check
```

Depuis `frontend/` :

```sh
env NODE_OPTIONS=--no-experimental-webstorage npm test
npm run build
env NODE_OPTIONS=--no-experimental-webstorage npx playwright test tests/e2e/territorial.spec.ts
```

Les premiers tests navigateur et Vitest ont nécessité deux corrections de recette : import de la fixture JSON adapté à l’environnement DOM, puis lecture HTTP de l’export depuis son lien plutôt qu’un téléchargement Playwright annulé par le navigateur. Le corps JSON exporté est également contrôlé par l’intégration API réelle. Les passages finaux sont réussis.

## Limites et portée

- Aucune nouvelle consultation IGN réelle n’est nécessaire à cette couche : le connecteur reste inchangé. Les preuves réelles antérieures de Caen et Carentan restent dans [la recette territoriale](TERRITORIAL_VALIDATION.md).
- Les observations et sources scientifiques des tests de qualification sont synthétiques et ne sont pas ajoutées au corpus utilisateur.
- Une observation humaine ou une intersection peut contextualiser l’étude d’une option ; elle ne valide ni sa faisabilité, ni son efficacité locale.
- La recherche lexicale automatique ne réalise pas l’examen d’applicabilité scientifique d’une alternative. En l’absence de ce travail, les options restent exploratoires ou contextualisées. Elles apportent néanmoins des variantes de conception concrètes.
- Les propositions ne comparent pas automatiquement deux géométries, ne dimensionnent pas les travaux, n’évaluent pas les coûts et ne quantifient aucun gain écologique.
- Les analyses historiques ne sont pas réécrites : lancer une nouvelle analyse pour obtenir les alternatives. Les droits, formulaires en lecture seule, modes et mécanismes de révision sont conservés.
- La compensation reste non évaluée. Aucune fusion ni aucun déploiement n’est réalisé.

Le [guide d’utilisation et de contrat](PROJECT_DESIGN.md) détaille les options et les références générales.
