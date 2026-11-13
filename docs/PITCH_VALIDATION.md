# Validation du pitch Symbiose — 13 novembre 2026

Le [script chronométré et la couverture du jury](PITCH_DATATHON_2026.md) sont
générés depuis `frontend/src/experience/pitch.ts`. Les huit paysages et les sept
transitions existants sont conservés. Le repère spatial de 210 unités est relié
au déroulé éditorial de 300 secondes, dont 90 secondes de démonstration manuelle.

## Sources effectivement examinées

- Manifeste ARQ : 13 pages, texte extrait et captures examinées, notamment les
  pages 5 et 7. La capture de remplacement provient de l'image originale de
  validation humaine, page 7, extraite sans retouche.
- Annexe du règlement : 5 pages ; six critères d'évaluation au § 5, page 3.
  La mention emploi-formation du § 3 et la note biodiversité sont conservées
  explicitement dans le carnet, sans réécriture du document officiel.
- Descriptif DOCX : trame vierge à sept rubriques. Aucun résultat nouveau n'en
  est déduit ; le manifeste fournit les réponses rédigées.
- Image des cinq questions : problème, solution, impacts, équipe, changement
  d'échelle ; chaque question possède sa correspondance dans le tableau du jury.
- Guides locaux de vision, validation humaine, parcelles, Open Data, RAG et
  alternatives ; recettes et archives IGN/DREAL existantes.

Les instantanés documentaires sont embarqués dans le frontend afin de conserver
le build Docker autonome et la lecture locale des sources. Les empreintes des
archives IGN et leur contenu sont comparés aux fichiers originaux par les tests.
Les services externes ne sont pas reconsultés par la présentation.

## Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| Vitest, suite frontend complète | 25 fichiers, **131 tests réussis** |
| Playwright : pitch, narration, espaces authentifiés et navigation des logos | **27 scénarios réussis**, en un passage complet |
| Contrôle mobile après ajustement de la visibilité du CTA | **1 scénario réussi**, position du bouton entièrement dans le cadre vérifiée |
| TypeScript/Vite local et build dans l'image Docker frontend | Réussis ; avertissement de taille du bundle 3D conservé |
| Export du pitch et des instantanés (`--check`) | À jour ; 392 mots hors vidéo, 300 secondes prévues |
| `git diff --check` | Réussi |
| Contrôle sur Nginx après reconstruction et redémarrage du frontend | HTTP 200, WebGL prêt, plein écran activé puis quitté, CTA `/connexion`, aucune requête distante ni erreur JavaScript |

Les tests navigateur vérifient les arrêts entre chapitres, le retour arrière,
la navigation clavier, la reprise du scroll natif, le redimensionnement, les
sources locales, la matrice d'archives, les statuts éditoriaux, l'accès à la
connexion et la conservation des espaces client et administrateur. Les contrôles
Axe couvrent les scènes mobiles et le carnet ; ce contrôle automatisé ne remplace
pas une évaluation humaine complète de l'accessibilité.

Une vidéo WebM générée comme **signal de test**, jamais distribuée comme vidéo
produit, valide une lecture réelle dans Chromium : absence d'autoplay, lancement,
pause, arrêt pendant le carnet et libération en quittant la scène. Un fichier
illisible vérifie le retour à la capture. Le refus ou l'absence de plein écran
affiche un message explicite. Ces vérifications ne lancent aucun
modèle IA ni entraînement.

Les corrections de recette incluent la précision des destinations de chapitre,
l'ordre des événements de molette avec ScrollTrigger, la réutilisation du tween
pendant la lecture, la priorité des boutons de navigation et la concordance des
points de vue fixes avec le texte en mouvements réduits.

## Captures

- [Problème](../output/symbiose/pitch/01-probleme.png)
- [Archives territoriales](../output/symbiose/pitch/03-donnees.png)
- [Chaîne technique](../output/symbiose/pitch/05-moteur.png)
- [Remplacement de la vidéo](../output/symbiose/pitch/06-demonstration.png)
- [Conclusion](../output/symbiose/pitch/08-conclusion.png)
- [Conclusion mobile](../output/symbiose/pitch/mobile-conclusion.png)
- [Démonstration sous Nginx / WebGL](../output/symbiose/pitch/06-demonstration-nginx.png)
- [Conclusion sous Nginx / WebGL](../output/symbiose/pitch/08-conclusion-nginx.png)
- [État du contrôle Nginx, Chromium 156.0.8078.4](../output/symbiose/pitch/production-smoke.json)

Les six premières captures utilisent le repli 2D pour rendre la recette éditoriale
reproductible. Les deux captures Nginx montrent le monde WebGL servi par le frontend
Docker actualisé, dont le service est sain sur le port 8080. La suite narrative teste également le monde WebGL et la perte de
contexte. Aucune performance graphique universelle n'est déduite de ces essais.

## Lancement et limites

```powershell
# À la racine : actualiser le frontend uniquement.
docker compose up -d --build --no-deps frontend
# Ouvrir http://localhost:8080/ hors session.
```

La vidéo sera montée ultérieurement par l'équipe. Ajouter
`frontend/public/experience-media/demo.mp4` ou `demo.webm`, puis reconstruire.
La sélection d'un fichier local depuis la scène fonctionne aussi, sans
téléversement ni persistance après rechargement. Prévoir les sous-titres WebVTT
du montage réel. Les chemins et le CTA se configurent au build dans
`frontend/.env.local`, comme décrit dans le pitch et le README des médias.

Le compteur est une position dans le script, pas un chronomètre réel de parole
ou de lecture du fichier. La répétition orale de cinq minutes avec la vidéo de
90 secondes reste à effectuer. Les terrains pilotes, l'accompagnement naturaliste
et les moyens de consolidation sont des besoins proposés, à confirmer par ARQ.
Aucun bénéfice écologique mesuré, score de reconnaissance, budget, rôle individuel
ou partenariat non documenté n'est ajouté. La finition artistique reste celle de
l'étude spatiale existante, avec ses ressources de production encore manquantes.
