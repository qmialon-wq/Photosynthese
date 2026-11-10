# Documents scientifiques — étape 6

> La pagination et la présentation ont évolué à l’étape 11 : grille responsive,
> choix de 4/8/12/16 documents, défaut de 16 et préférence locale indépendante.
> Voir [la pagination du corpus scientifique](PAGINATION_CORPUS_SYMBIOSE.md)
> pour le comportement actuel. La description de l’étape 6 ci-dessous conserve
> la trace de la maquette initiale.

La page graphique `/documents` complète les six rubriques de Symbiose, avec la stack Vue 3, TypeScript et Vue Router existante. Elle reprend la structure de la maquette : en-tête et actions, panneau Mon corpus avec sélection d’espèce et pagination, puis panneau Avancement distinct.

## Fichiers créés

- `frontend/src/pages/DesignDocumentsPage.vue` : état local, choix d’espèces, sélection limitée à la page, confirmations, import de noms de fichiers et temporisateurs de démonstration.
- `frontend/src/components/symbiose/DocumentList.vue` : liste réutilisable, métadonnées fictives, cases et action Consulter.
- `frontend/src/components/symbiose/DocumentEmptyState.vue` : état vide réutilisé dans Mon corpus et Avancement.
- `frontend/src/components/symbiose/RetrievalProgress.vue` : affichage des états En attente, En cours et Terminé et barre de progression.
- `frontend/src/data/document-preview.ts` : espèces, exemples fictifs, compteurs, sélection, extensions autorisées et scénario de progression.
- `frontend/src/styles/scientific-documents.css` : styles propres aux documents, préfixés `sd-`.
- `frontend/tests/unit/document-preview.test.ts` et `frontend/tests/e2e/documents-design.spec.ts` : tests de cette étape.
- `docs/DOCUMENTS_SYMBIOSE.md` : cette documentation.

## Fichiers modifiés

- `frontend/src/router.ts` : remplace uniquement la route provisoire Documents scientifiques par la nouvelle page.
- `frontend/src/components/symbiose/Pagination.vue` : ajoute une variante facultative `simple` avec Page précédente / Page N / Page suivante. La variante numérotée reste la valeur par défaut et conserve le rendu des autres pages.
- `frontend/src/components/symbiose/SymIcon.vue` : ajoute les pictogrammes téléchargement, import, boîte documentaire et avancement. Les pictogrammes de navigation restent identiques.
- `frontend/src/styles/symbiose.css` : ajoute deux règles desktop limitées au bouton actif Documents pour permettre son libellé sur deux lignes dans la pilule de 186 × 62 px. Fond, bordure, ombres et position restent identiques à l’Accueil.
- `docs/DESIGN_SYMBIOSE.md` : indique que les six rubriques sont désormais intégrées graphiquement.

AppShell, WheelNavigation, GlassPanel, FilterSelect, DemoDialog, les boutons secondaires, les cases et la pagination sont réutilisés. Le code de la roue, ses six positions, son arc et ses animations ne sont pas modifiés. Aucune autre page n’est réécrite.

## États et interactions

L’état initial affiche exactement Renard · 0 documents, un corpus vide, un compteur 0 sélectionné(s), une suppression et une pagination désactivées, et Aucune récupération en cours. Des exemples explicitement fictifs sont disponibles en sélectionnant Chevreuil, Sanglier ou Blaireau ; ils ne remplissent pas le panneau Renard au chargement.

Changer d’espèce ou de page réinitialise la sélection. Les compteurs proviennent des entrées effectivement présentes dans l’état local. La pagination montre deux documents par page. Retirer du corpus nécessite une confirmation, agit uniquement sur les entrées sélectionnées de la page visible, puis recalcule le compteur et la page courante. Annuler ne change aucune entrée. Aucun fichier réel n’est supprimé.

Consulter ouvre une modale de démonstration avec les métadonnées fictives. Aucun titre n’est présenté comme une publication authentique, aucun DOI ou lien scientifique n’est fabriqué et aucun document n’est ouvert ou téléchargé.

Importer un document ouvre le sélecteur local pour PDF, DOCX et TXT. Seuls le nom et l’extension sont utilisés ; le contenu du fichier n’est jamais lu. La confirmation ajoute une entrée fictive au corpus courant. Annuler ne l’ajoute pas. Les extensions non prévues produisent un message ; ce message disparaît après le choix d’un fichier accepté. Le fichier source reste intact, n’est pas envoyé et n’est pas conservé par l’application.

Récupérer pour toutes les espèces demande une confirmation explicite de simulation et concerne toujours les cinq espèces. Choisir les espèces ouvre une liste multiple annulable ; Confirmer lance la même démonstration pour les seules espèces cochées. Les boutons sont désactivés pendant une tâche afin d’éviter les simulations simultanées.

Une tâche reste d’abord En attente pendant 700 ms, passe En cours et avance toutes les 350 ms, puis se termine après six étapes. Un exemple explicitement fictif est ajouté pour chaque espèce concernée. Il ne s’agit pas d’une publication récupérée. L’objectif de 100 articles n’est pas présenté comme atteint par ces exemples. Les temporisateurs sont arrêtés en quittant la page.

Toutes les modifications restent en mémoire. Recharger ou revenir sur la page restaure l’état initial. Aucune recherche réelle, API documentaire, collecte, lecture de fichier, IA, base de données, localStorage ou sessionStorage n’est ajoutée.

## Lancement et contrôles

Depuis `frontend/` :

```powershell
npm run dev -- --port 4173
npm run build
npm test
npx playwright test tests/e2e/documents-design.spec.ts tests/e2e/validation-design.spec.ts tests/e2e/analyse-design.spec.ts tests/e2e/symbiose-design.spec.ts tests/e2e/videotheque-design.spec.ts tests/e2e/dossiers-design.spec.ts tests/e2e/profile-logout.spec.ts
```

Les tests de la page vérifient l’état vide, l’accessibilité, les six positions et l’ordre de la roue, la pilule active, le choix d’espèces, les compteurs, la pagination, la sélection, les confirmations, les imports, les états de progression et leur nettoyage, les cas vides et le mobile à 390 px. Les simulations d’import et de récupération sont également contrôlées sans requête réseau et sans stockage permanent.

Les cinq pages précédentes sont comparées avant et après un passage par Documents scientifiques : captures hors liens animés et note de démonstration, puis géométrie, styles et pictogrammes de chaque lien vérifiés séparément.

Les six captures finales sans masquage à 1600 × 900 sont conservées dans `output/symbiose/etape-6/` :

- `documents-scientifiques-1600x900.png`
- `accueil-1600x900.png`
- `videotheque-1600x900.png`
- `mes-dossiers-1600x900.png`
- `analyse-video-1600x900.png`
- `validation-humaine-1600x900.png`
