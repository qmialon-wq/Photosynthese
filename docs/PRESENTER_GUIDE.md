# Symbiose — guide du présentateur

> Decors actualises : revision **31c94db9b955178c**, pack `Symbiose-jury-2026.zip`. Apres un changement de version, recharger en ligne et actualiser l'installation hors ligne, puis refaire le test de rechargement hors connexion. Le mode `?render=2d` et le PDF restent les secours sans GPU.


## Avant la séance

1. Construire la production et ouvrir `http://localhost:8080/jury/` dans le profil
   Chromium préparé pour la séance. Cette entrée n'attend pas la connexion métier.
2. Vérifier le bon fichier vidéo. Le montage produit de 90 secondes est encore
   absent à cette livraison : la capture affichée ne constitue pas une démo vidéo.
3. Si le montage existe, le placer dans `frontend/public/experience-media/`,
   reconstruire puis actualiser l'installation. Vérifier son cadrage, sa durée,
   ses sous-titres et les sources visibles. Le son est muet par défaut ; le
   réactiver seulement si nécessaire, par un geste explicite.
4. Dans **Préparation du jury**, cliquer **Installer hors ligne**. Attendre la
   réussite. Une configuration média explicite dont le fichier manque n'est pas
   acceptée par le build. L'absence du montage non configuré reste signalée.
5. Couper le réseau dans le navigateur et recharger la page. Visiter les huit
   chapitres, ouvrir les sources et essayer la vidéo réelle lorsqu'elle sera
   fournie. Garder le même navigateur, le même profil et la même adresse.
6. Ouvrir **Régie du récit → Recommencer le récit**. Tester le plein écran sur le
   vidéoprojecteur réel ; régler son contraste et la mise à l'échelle de Windows.
7. Répéter le script avec le montage. Le compteur indique une position dans le
   récit, pas la durée réelle de parole. Cinq minutes restent une cible à répéter.

## Pendant les cinq minutes

| Créneau | Chapitre | Action |
|---|---|---|
| 0:00–0:35 | Forêt | Poser le problème de la connaissance locale dispersée |
| 0:35–1:00 | Ciel | Nommer Symbiose et ses bénéficiaires |
| 1:00–1:35 | Rivières | Expliquer les données réellement mobilisées et leurs limites |
| 1:35–1:55 | Monde sous-marin | Annoncer explicitement les perspectives futures |
| 1:55–2:30 | Zone humide | Distinguer détection, classification, suivi et contrôle humain |
| 2:30–4:00 | Prairie et bocage | Lancer la vraie vidéo manuellement lorsqu'elle sera disponible |
| 4:00–4:25 | Littoral | Distinguer bénéfices attendus et résultats techniques documentés |
| 4:25–5:00 | Forêt nocturne | Présenter ARQ, les besoins proposés et le CTA |

Le [texte oral et le tableau du jury](PITCH_DATATHON_2026.md) restent la référence.
La validation d'une espèce et l'efficacité d'un aménagement ne sont pas déduites
des illustrations ou des résultats de tests techniques.

## Commandes

| Commande | Comportement |
|---|---|
| Flèches gauche/droite, Page précédente/suivante | Changer de chapitre en présentation |
| Début / Fin | Début ou conclusion |
| Espace hors contrôle interactif | Lecture/pause du récit jusqu'au prochain arrêt |
| Les huit repères latéraux | Retour immédiat au chapitre dans le mode jury |
| Démonstration | Aller directement au créneau 2:30 |
| Plein écran | Entrer/sortir explicitement du plein écran |
| Régie → Passer l'animation | Avancer immédiatement, sans attendre le déplacement |
| Régie → Recommencer | Rembobiner et réinitialiser le lecteur, sans relancer de modèle |
| Régie → Reprendre | Rejoindre le point sauvegardé avant le rechargement |
| Régie → Secours sans WebGL | Libérer le monde 3D et continuer avec les images 2D |

Les formulaires, le lecteur vidéo, les dialogues et les menus gardent leurs
touches natives. Échap ferme le carnet et ne doit pas changer le chapitre ni
effacer le fichier vidéo ouvert. Avec les mouvements réduits du système, les
points de vue sont fixes et la lecture animée est désactivée.

## Incident pendant le pitch

- **GPU ou WebGL défaillant** : le repli 2D se déclenche automatiquement après une
  perte de contexte. Pour l'imposer, utiliser la régie ou `/jury/?render=2d`.
  Le texte, les huit étapes, la vidéo locale et les sources restent accessibles.
- **Navigateur fermé ou page rechargée** : ouvrir la même adresse et le même profil,
  puis **Régie → Reprendre**. La sauvegarde porte sur le chapitre et le mode ; une
  lecture vidéo ne reprend jamais seule. Un fichier choisi temporairement doit
  être sélectionné à nouveau ; le montage embarqué reste disponible.
- **Installation incomplète ou données navigateur effacées** : garder le serveur
  local actif. Le message d'échec n'est pas transformé en réussite. Réinstaller
  avant la séance, pas pendant la parole.
- **Navigateur inutilisable** : ouvrir la galerie de captures depuis
  `output/symbiose/final/` ou le [PDF fixe de huit pages](../output/symbiose/final/secours-symbiose.pdf), lire le script écrit et lancer le montage dans le
  lecteur local du PC lorsqu'il sera fourni. Les captures sont un support fixe,
  pas une démonstration réelle ni une mesure écologique.
- **Application finale indisponible** : terminer le récit et nommer la limite.
  L'accès à Symbiose exige ses services ; le pack du jury ne les simule pas.

Le test hors ligne automatisé ne remplace pas cette répétition sur le matériel
de la salle. Firefox, Safari, lecteur d'écran humain et vidéoprojecteur doivent
faire l'objet d'une recette distincte si ces conditions seront utilisées.

Pour la projection, la version 2D reprend les compositions d'intention et évite
la reconstruction 3D encore schématique. Elle constitue aujourd'hui le choix
le plus proche de la planche artistique. Les deux modes restent accessibles ;
tester et choisir celui de la séance avant l'arrivée du jury.
