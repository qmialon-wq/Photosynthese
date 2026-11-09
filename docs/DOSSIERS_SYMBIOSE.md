# Symbiose — Étape 3 : Mes dossiers

La route `/parcelles` affiche `frontend/src/pages/DesignProjectsPage.vue`. Cette étape reste graphique : douze dossiers fictifs, six résultats par page, recherche par nom, filtres combinés par type de projet et statut, pagination locale, survol des cartes et aperçu de démonstration. Aucun stockage, traitement, upload ou appel API n’a été ajouté.

## Réutilisation et périmètre

`AppShell`, `WheelNavigation`, les coordonnées des six positions, les icônes, le fond forestier et les sources de l’Accueil, de la Vidéothèque et de la Connexion restent inchangés. La rubrique Mes dossiers utilise la quatrième position avec la même pilule verte translucide de 186 × 62 px que l’Accueil en 1600 × 900.

Les composants existants `GlassPanel`, `SearchField`, `FilterSelect`, `Pagination`, `StatusBadge`, `SymIcon` et `DemoDialog` sont réutilisés. Les styles des contrôles sont importés depuis `styles/videotheque.css`, sans duplication ni modification. Les seuls styles complémentaires sont isolés sous les classes `sf-*` dans `styles/dossiers.css`.

Deux propriétés optionnelles rendent les composants existants réutilisables : `Pagination.itemLabel` et `navigationLabel` gardent leurs valeurs par défaut « vidéo » et « Pagination des vidéos » ; `StatusBadge.label` permet « Validé » sans changer le libellé par défaut « Validée » ni les couleurs de statut. Aucune variante graphique n’est ajoutée.

`ProjectCard.vue` regroupe la photographie, le badge, les métadonnées et un menu natif accessible au clavier. Un clic ouvre un aperçu explicitement fictif. Le bouton « Choisir ou importer des vidéos » mène à la Vidéothèque existante.

## Données

`frontend/src/data/project-preview.ts` centralise les douze dossiers et les options de filtres. Les six premières entrées reproduisent les noms, compteurs et statuts demandés. La deuxième page complète la démonstration. La recherche ignore la casse et les accents ; un changement de filtre revient à la première page.

## Vérification et captures

Depuis `frontend/` :

- `npm run dev` : lancer l’application.
- `npm run build` et `npm test` : compiler et vérifier les tests unitaires.
- `npx playwright test tests/e2e/dossiers-design.spec.ts tests/e2e/videotheque-design.spec.ts tests/e2e/symbiose-design.spec.ts tests/e2e/profile-logout.spec.ts` : vérifier les trois pages et leurs interactions communes.

Le test de l’étape 3 réalise trois captures en 1600 × 900 et compare l’Accueil et la Vidéothèque avant/après un aller-retour par Mes dossiers. Les images de livraison sont complètes. Pour éviter les faux écarts liés à la recomposition GPU du verre et de l’anticrénelage après animation, seuls les boutons de la roue et la note de démonstration sont masqués dans la comparaison automatique des pixels. Les six libellés, positions, tailles, fonds, bordures, ombres, polices et tracés des icônes de la roue sont comparés séparément avant/après ; l’arc SVG reste également vérifié.

Les captures finales sont conservées dans `output/symbiose/etape-3/` : `mes-dossiers-1600x900.png`, `accueil-1600x900.png` et `videotheque-1600x900.png`.

## Photographies

Les cartes de forêt réutilisent `frontend/src/assets/auth-forest.png`, avec un cadrage CSS préservant les proportions. Le bocage réutilise la photographie de campagne de `biodiversity-thumbnails.png`.

Les paysages complémentaires de vallée, de zone humide et de prairie sont enregistrés dans `frontend/src/assets/project-landscapes.png`. Cette planche de trois photographies a été préparée avec l’outil intégré `image_gen` et affichée par position d’arrière-plan CSS, sans capture d’interface ni service de génération dans l’application.

Consigne exacte :

> Create a photographic contact sheet made of EXACTLY THREE wide landscape photos stacked vertically, each filling one third of the image height. Overall image square, each individual photo is a panoramic 3:1 landscape. No margins, no gaps, no borders. Photo 1 in the TOP THIRD: a lush green forested European valley and rolling hills with layered misty ridges under soft warm early morning sky. Photo 2 in the MIDDLE THIRD: a calm natural wetland pond or slow river at sunset, green trees and meadow along its banks, golden sunlight reflected on the water. Photo 3 in the BOTTOM THIRD: a wildflower meadow with pink wildflowers in the foreground, green grass, leafy forest edge and bright soft sunlight. Each photo independently composed, premium realistic nature photography, rich natural forest greens and warm natural light. No text, no letters, no symbols, no logos, no map, no line drawings, no frames, no interface or icons, no people or animals. These will be tiny scenic thumbnails in a biodiversity application.

