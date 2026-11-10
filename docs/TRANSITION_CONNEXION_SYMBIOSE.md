# Transition de connexion Symbiose

Après la confirmation de `/auth/login`, `AuthPage.vue` conserve `acceptSession`,
le passage aux données réelles et la destination `/`. Elle démarre seulement la
présentation avant la navigation, sans attendre sa fin ni les données métier.
L’inscription, l’initialisation et les autres navigations ne la démarrent pas.

## Fichiers

- `frontend/src/components/symbiose/LoginTransition.vue` : couche globale montée
  dans `App.vue`, paysage du thème choisi, brume, particules, logo, annonce et
  bouton « Passer ». Les couleurs utilisent `--sym-primary`, `--sym-secondary`
  et `--sym-accent`, communs aux huit environnements.
- `frontend/src/components/symbiose/GallopingDeer.vue` : dessin vectoriel original
  créé pour le projet, sans ressource distante ni dépendance supplémentaire.
  Quatre pattes articulées, flexion des genoux/jarrets, décalage des membres
  éloignés, oscillation du corps et compensation de la tête. Les bois restent
  solidaires de la tête.
- `frontend/src/composables/useLoginTransition.ts` : état partagé non persistant,
  identifiant par exécution, promesse d’achèvement et nettoyage idempotent.
- `frontend/tests/unit/login-transition.test.ts` et
  `frontend/tests/e2e/login-transition.spec.ts` : vérifications du cycle de vie et
  du parcours navigateur.

## Durées et accessibilité

La présentation dure 2 800 ms, dont 2 200 ms de traversée après un délai de
150 ms. Le cycle de galop dure 600 ms. Le fondu de révélation commence vers
2 350 ms. Un délai indépendant retire systématiquement la couche après
3 100 ms, même sans événement CSS.
Une erreur de navigation annule immédiatement la présentation et conserve
l’erreur affichée par le formulaire. Les exécutions anciennes ne peuvent pas
annuler une nouvelle animation.

Les préférences système et Symbiose donnent une variante statique de 120 ms,
sans cerf ni particules ; son délai de sécurité est de 420 ms. Activer la
réduction pendant une animation la termine immédiatement.

L’annonce « Connexion réussie. Ouverture de votre espace Symbiose. » utilise une
région vivante. Les éléments décoratifs sont masqués aux lecteurs d’écran.
Le bouton « Passer » reçoit le focus pendant la variante animée et le restitue
au contenu à la fermeture s’il le possède encore. Il n’y a ni piège clavier,
ni verrouillage du défilement, ni neutralisation des interactions de l’Accueil.
« Passer » termine seulement la présentation ; la navigation et la session
continuent normalement.

## Lancement et vérification

Depuis `frontend` :

```powershell
npm install --ignore-scripts
npm run dev
npm test
npm run build
npx playwright test tests/e2e/login-transition.spec.ts tests/e2e/login-design.spec.ts tests/e2e/authentication.spec.ts
# Avec Vite déjà lancé : enregistrement continu desktop et mobile
node scripts/record-login-transition.mjs http://127.0.0.1:5173
```

Utiliser Node 22.12 ou plus récent pour satisfaire les exigences déjà présentes
de l’outil d’audit d’accessibilité. Playwright démarre Vite sur le port 4173 s’il
n’y a pas de serveur de test. Les vidéos et captures de chaque scénario sont
dans `frontend/test-results`. Des preuves sélectionnées sont conservées dans
`output/symbiose/etape-17`.

Vérification réalisée : 114 tests unitaires réussis, compilation TypeScript/Vite
réussie, 17 nouveaux scénarios navigateur réussis et 5 scénarios existants
d’authentification/design vérifiés. Le jeu de réponses du test de nouvelle
tentative a été corrigé : `/auth/me` doit confirmer la session après une
connexion réussie, puisque le fournisseur de données réelles la vérifie.

`parcours-desktop.webm` et `parcours-mobile.webm` sont des prises continues,
sans pause des animations ni capture fixe pendant la traversée. Le script
d’enregistrement vérifie aussi l’arrivée à l’Accueil et l’absence de couche
persistante. La capture mobile du test de composition fige volontairement une
pose pour examiner la disposition ; la vidéo continue est la référence pour
évaluer le mouvement.

Les tests navigateur interceptent explicitement les réponses HTTP pour couvrir
réussite, refus, serveur absent, réponses rapides/lentes et données métier
indisponibles. Ces enregistrements démontrent le parcours visuel, pas une
authentification contre un serveur réel. La fluidité est vérifiée dans Chromium
par l’évolution des transformations et l’examen des images de la vidéo ; elle
reste à apprécier sur les appareils et navigateurs de déploiement. Le cerf est
une silhouette vectorielle stylisée, sans simulation biomécanique.
