# Personnalisation du fond — Étape 15

L’engrenage en bas à gauche ouvre le menu des paramètres et l’accès administratif autorisé. « Paramètres d’affichage » regroupe la source de données existante, la réduction des animations et huit fonds photographiques. La galerie utilise des boutons radio natifs, deux colonnes, une sélection citron et une validation visible. Le corps du panneau défile ; son titre et sa fermeture restent accessibles.

## Ressources

La forêt d’origine est convertie sans perte et conserve exactement ses pixels et sa composition. Les sept autres photos Unsplash sont téléchargées localement en WebP 2560 × 1440. Huit miniatures séparées de 320 × 180 totalisent environ 57 Kio, contre 4,8 Mio pour les huit grandes images. Le navigateur charge uniquement les grandes photos demandées.

| Environnement | Ressource | Crédit |
| --- | --- | --- |
| Forêt | `forest.webp` | Fond Symbiose original, issu de `home-forest.png` |
| Ciel et nuages | `sky.webp` | [Artem](https://unsplash.com/photos/8_uRtr9QUS0) |
| Rivière | `river.webp` | [Billy Freeman](https://unsplash.com/photos/TyOuzLDcqiE) |
| Monde sous-marin | `underwater.webp` | [Erick Morales Oyola](https://unsplash.com/photos/vHDLjO-iW8k) |
| Zones humides | `wetland.webp` | [Pascal Debrunner](https://unsplash.com/photos/2lPR-5MUliw) |
| Prairie et bocage | `meadow.webp` | [Tanya Barrow](https://unsplash.com/photos/c7Igx8X-XRI) |
| Littoral | `coast.webp` | [Sergei Gussev](https://unsplash.com/photos/aoY9DHy334Y) |
| Forêt nocturne | `night-forest.webp` | [Mike Dierken](https://unsplash.com/photos/t1QCaQ9vu6E) |

Les crédits, identifiants des originaux, traitements et conditions Unsplash sont conservés dans [SOURCES.md](../frontend/src/assets/backgrounds/SOURCES.md). La localisation du bocage n’est pas précisée par la source ; seule la photo du littoral est présentée comme normande.

## Architecture et fichiers

Créations :

- `frontend/src/config/background-themes.ts` : noms, descriptions, URLs locales, positions, voiles de contraste et crédits des huit thèmes.
- `frontend/src/composables/useWallpaper.ts` : instance partagée indépendante du mode de données, validation/restauration, préchargement et décodage, arbitrage des sélections rapides, persistance et erreurs.
- `frontend/src/components/symbiose/WallpaperBackground.vue` : deux couches fixes et voile propre à chaque photo.
- `frontend/src/components/symbiose/DisplaySettings.vue` : contenu commun du panneau, galerie accessible et restauration de la forêt.
- `frontend/src/components/symbiose/AppearanceMenu.vue` : accès aux mêmes réglages depuis les layouts administratif et historique du profil.
- `frontend/src/styles/wallpaper.css` : galerie, dimensions et défilement du panneau, fondu et adaptations mobiles.
- `frontend/src/assets/backgrounds/` : huit fonds, huit miniatures et provenance.
- `frontend/tests/unit/wallpaper.test.ts`, `frontend/tests/e2e/wallpaper.spec.ts` et `frontend/tests/e2e/display-settings.ts` : tests et accès commun aux réglages.

Modifications :

- `AppShell.vue`, `AdminShell.vue` et `App.vue` : application du même fond dans les six rubriques, l’administration et le profil, en conservant la structure des layouts.
- `ModeSelector.vue` et `data-mode.css` : libellé visible « Source de données » dans les réglages, réemploi du store métier existant.
- `symbiose.css` : remplacement du fond figé par les couches partagées ; retrait des styles exclusifs à l’ancienne recherche globale.
- `main.ts` : chargement de la feuille de style.
- Tests navigateur `admin-design`, `data-modes`, `document-pagination`, `symbiose-design` : adaptation au déplacement du sélecteur hors de l’en-tête et au retrait de la recherche globale.

Le sélecteur de données existe exclusivement dans le panneau de réglages. L’en-tête d’observation conserve les notifications et le profil. La roue, les six rubriques, les composants métier, les API et `data-mode.ts` ne sont pas modifiés.

## Comportement

- Préférence : `symbiose:wallpaper:v1`, identifiant validé, défaut `forest`.
- Réduction des animations : `symbiose:reduce-motion:v1`, combinée à `prefers-reduced-motion`. Les deux préférences restent séparées des données et des comptes.
- Décodage de la nouvelle photo avant affichage, fondu de 650 ms et deux couches maximum, même après plusieurs choix rapprochés. Réduction des animations : application directe.
- Une photo en erreur conserve la précédente et affiche un message dans les paramètres. Un échec du stockage conserve le choix pour la session.
- La restauration ne change que le fond. Aucun appel serveur n’est ajouté pour le papier peint ; le contrôle de session du menu administratif reste en place.
- Connexion conserve son propre fond. Aucun changement aux formulaires ni aux fonctions du profil.
- Le titre et le pied de page du layout historique du profil gardent leurs couleurs et reçoivent une surface claire, afin de rester lisibles devant les photos.

## Lancement et vérifications

Depuis `frontend/` :

```powershell
npm run dev -- --port 4173
npm run build
npm test
npx playwright test tests/e2e/wallpaper.spec.ts tests/e2e/wheel-motion.spec.ts tests/e2e/symbiose-design.spec.ts tests/e2e/data-modes.spec.ts tests/e2e/admin-design.spec.ts tests/e2e/document-pagination.spec.ts tests/e2e/profile-logout.spec.ts --output=test-results/appearance-regression --reporter=line
```

Les tests navigateur utilisent des sessions et des réponses API contrôlées. Ils vérifient l’interface et la préservation des protections et des modes ; ils ne constituent pas une exécution des traitements backend, GPU ou documentaires réels.

Résultats :

- `npm run build` : compilation TypeScript et production réussies.
- `npm test` : 96 tests unitaires réussis, dont 12 nouveaux cas pour les préférences, les erreurs, les accès au stockage et les changements concurrents.
- 64 scénarios Playwright validés : 61 réussis lors de la série complète, puis les trois scénarios dont les assertions nécessitaient une adaptation rejoués avec succès. Aucun échec fonctionnel restant.
- Huit fonds sélectionnés individuellement et photographies visibles ; le démarrage ne demande qu’une grande image, puis les suivantes uniquement lorsqu’elles sont sélectionnées.
- Contrôles Axe WCAG 2 A/AA et 2.1 AA sans violation pour chacun des huit fonds avec la galerie ouverte. Inspection visuelle des captures desktop, mobile, administration et profil.
- Après protection du titre et du pied de page du profil par une surface claire, le scénario de navigation commun et le contrôle Axe du profil ont été rejoués avec succès.
- Conservation de la sélection après rechargement, navigation des six rubriques, ouverture du profil et administration ; cohérence du mode global, lecture seule, simulations et contrôles de permission vérifiés par les scénarios existants.
- Échec de chargement : message discret, fond et préférence précédents conservés. Stockage bloqué et réponses de chargement tardives vérifiés en tests unitaires.
- Deux couches pendant le fondu, clavier natif, choix rapides, réglage de réduction et préférence système vérifiés.
- Panneau dans les limites de l’écran, défilement, fermeture et focus à 800 × 600, 390 × 844 et 320 × 568, y compris après fermeture du tiroir administratif.
- Égalité des dimensions et de tous les pixels RGB de `forest.webp` avec `home-forest.png`, vérifiée avec Pillow.

Captures disponibles dans [output/symbiose/etape-15](../output/symbiose/etape-15/) :

- [Aperçu des huit environnements](../output/symbiose/etape-15/apercu-huit-fonds.jpg).
- Huit vues à 1600 × 900 : [Forêt](../output/symbiose/etape-15/forest-1600x900.png), [Ciel](../output/symbiose/etape-15/sky-1600x900.png), [Rivière](../output/symbiose/etape-15/river-1600x900.png), [Sous-marin](../output/symbiose/etape-15/underwater-1600x900.png), [Zones humides](../output/symbiose/etape-15/wetland-1600x900.png), [Prairie](../output/symbiose/etape-15/meadow-1600x900.png), [Littoral](../output/symbiose/etape-15/coast-1600x900.png), [Forêt nocturne](../output/symbiose/etape-15/night-forest-1600x900.png).
- [Panneau desktop](../output/symbiose/etape-15/parametres-1600x900.png), [800 px](../output/symbiose/etape-15/settings-800.png), [390 px](../output/symbiose/etape-15/settings-390.png), [320 px](../output/symbiose/etape-15/settings-320.png).
- [Administration avec Littoral](../output/symbiose/etape-15/admin-coast-1600x900.png) et [profil avec Rivière](../output/symbiose/etape-15/profil-river-1600x900.png).

Aucune image ni fonctionnalité demandée ne reste à intégrer. Les traitements métier réels nécessitent toujours les services habituels ; ils n’ont pas été exécutés pour cette modification d’apparence.
