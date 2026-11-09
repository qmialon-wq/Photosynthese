# Symbiose — Étape 11 : pagination du corpus scientifique

La page `/documents` propose une grille de cartes et un sélecteur **Documents par page** : **4, 8, 12 ou 16**, avec **16 par défaut**. Le contrôle FilterSelect existant est placé à droite de l’espèce ; les deux champs s’empilent sur mobile.

## Comportement

- La préférence est conservée sous `symbiose:documents-per-page:v1`, indépendamment de la Vidéothèque. Une valeur ancienne ou invalide revient à 16 ; un stockage bloqué n’empêche pas le contrôle de fonctionner.
- Changer de taille revient à la première page, conserve l’espèce et efface la sélection. Changer de page ou d’espèce conserve également la règle de réinitialisation existante.
- Le compteur utilise le corpus effectivement filtré : par exemple `1 – 16 sur 50 documents`. Le corpus vide affiche `0 document`, avec les deux boutons désactivés.
- La pagination indique aussi `Page 1 sur 4`. Pour 50 documents, les tailles 4/8/12/16 donnent respectivement 13/7/5/4 pages.
- « Tout sélectionner sur cette page » agit uniquement sur les cartes visibles. Le retrait conserve ses autorisations et sa confirmation existantes.

La grille utilise CSS Grid : quatre colonnes sur grand écran, deux jusqu’à 1390 pixels, puis une jusqu’à 650 pixels. La taille de page reste indépendante de ces colonnes. Les cartes d’une même ligne ont une hauteur homogène ; les titres restent affichés intégralement, sur plusieurs lignes, et peuvent augmenter la hauteur de leur ligne. La page défile naturellement sans tenter de faire tenir seize cartes dans un écran de 900 pixels.

Cases, icône de fichier, titre, espèce, format, date disponible et bouton Consulter sont conservés. Les cartes sélectionnées gardent leur bordure lumineuse. Le bouton reste en bas de carte.

## Modes de données et administration

**Démonstration :** les huit exemples existants sont conservés. Seize exemples explicitement fictifs complètent Blaireau, qui possède maintenant 17 documents. Le scénario contient donc 24 entrées. Renard reste vide, Chevreuil conserve cinq documents et Sanglier deux : ces cas permettent aussi de présenter les corpus vides ou courts. Aucun titre ajouté n’est présenté comme une publication authentique.

**Données réelles :** le provider existant fournit uniquement les documents disponibles. Aucune entrée de remplissage n’est créée. Les contrôles sont locaux et ne déclenchent pas de nouvelle requête documentaire. L’import, la récupération et le retrait conservent la lecture seule déjà prévue dans cet écran.

**Administration :** les styles de grille et de cartes verticales sont limités à `.sd-page`. DocumentList garde ses lignes administratives, les actions existantes et la sélection. Le traitement des imports, récupérations, retraits, consultations et suivis n’est pas modifié.

AppShell, WheelNavigation, les providers et le store des modes ne sont pas modifiés.

## Fichiers

| Fichier | Modification |
| --- | --- |
| `frontend/src/pages/DesignDocumentsPage.vue` | Taille réactive, sélecteur, calculs et sélection, compteur activé dans la pagination existante |
| `frontend/src/data/document-page-size.ts` | Valeurs autorisées, défaut, validation et stockage de la préférence |
| `frontend/src/components/symbiose/Pagination.vue` | Option `showCount`, désactivée sur les autres pages, pour afficher résultats et nombre de pages dans la variante simple |
| `frontend/src/components/symbiose/DocumentList.vue` | Titre intégral également disponible au survol ; structure et événements partagés conservés |
| `frontend/src/styles/scientific-documents.css` | Contrôles alignés, grille responsive et cartes verticales limitées à la vue d’observation |
| `frontend/src/data/document-preview.ts` | Suppression de la constante fixe de deux documents, enrichissement des exemples Blaireau |

Les tests documentaires et des modes ont été adaptés aux tailles désormais autorisées. Les contrôles unitaires vérifient aussi les compteurs, les préférences invalides ou bloquées et le maintien du comportement par défaut de Pagination sur les autres pages.

## Vérifications

Depuis `frontend/` :

```powershell
npm run build
npm test
npx playwright test tests/e2e/document-pagination.spec.ts tests/e2e/documents-design.spec.ts tests/e2e/data-modes.spec.ts tests/e2e/admin-design.spec.ts tests/e2e/videotheque-design.spec.ts tests/e2e/harmonisation-design.spec.ts
```

Les nouveaux scénarios vérifient les tailles 4/8/12/16, les 50 documents et leurs dernières pages, les sélections partielles ou complètes, les changements de taille et d’espèce, la consultation, les cas vides ou courts, le rechargement, les modes, les longs titres, le clavier et l’accessibilité WCAG A/AA. Les dispositions sont contrôlées à 1600, 1100, 768 et 390 pixels. Une vérification dédiée contrôle les lignes, la consultation et la sélection de l’administration.

**Résultats :** compilation réussie, **71 tests unitaires réussis**, et **64 scénarios navigateur distincts validés**. La série complète a donné 63/64 ; un ancien test d’import enchaînait la réouverture avant l’événement natif de fermeture. Le test attend désormais cet événement. Les sept scénarios documentaires relancés passent tous, sans modification du mécanisme d’import. La synthèse retient le dernier résultat de chaque scénario ; les rapports bruts restent consultables dans la galerie.

Le scénario de volume utilise **506 publications fournies par une fixture API**, dont 501 pour Blaireau et cinq pour Chevreuil : le provider conserve ses trois lectures de 200 éléments maximum, aux offsets 0/200/400, et seulement 16 cartes sont montées. Les changements de pagination ne font pas de nouveaux appels ; toutes les requêtes de ce scénario restent des GET. Le temps observé figure dans l’annotation du rapport navigateur ; il ne constitue pas une mesure de performance d’un serveur de production.

La série complète mesure environ **1,99 seconde** pour charger ce scénario sur le poste de vérification, navigation comprise.

Les résultats automatisés et les captures 1600 × 900 à 4, 8 et 16 documents, la vue complète des seize cartes et les captures mobile et administration sont regroupés dans [la galerie de l’étape 11](../output/symbiose/etape-11/index.html).

La pagination porte sur le corpus chargé par le provider existant et conserve ses limites de lecture. La disponibilité d’un document ou de sa source originale dépend des métadonnées reçues. Aucun nouveau téléchargement, traitement documentaire ou service backend n’est ajouté.
