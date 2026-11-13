# Pipeline visuel et revue des assets

## Arborescence

```text
frontend/public/experience-art/
  index.html / gallery.css / gallery.js  prévisualisation locale fixe
  manifest.json                         inventaire global vérifié
  shared/symbiose-logo.png               copie inchangée du logo produit
  forest/ … night-forest/
    primary-v1.png                      composition générée
    foreground-v1.png                   candidat de premier plan avec alpha
    manifest.json                       inventaire de la scène
    prompts/primary.txt                 consigne exacte de génération
    prompts/foreground.txt              consigne exacte de détourage
    prompts/missing.json                consignes et spécifications des ressources absentes
```

Les emplacements futurs de clean plates, profondeurs, passes atmosphériques, GLB et vidéos sont déclarés par `expectedPath`. **Ils ne sont pas créés comme de faux fichiers vides.** Une ressource absente a `path: null`, `status: "missing"`, sans dimensions, licence acquise ou empreinte fictives.

## Reproduire la revue

Le Compose de base et le Dockerfile existant distribuent automatiquement le contenu de `frontend/public` dans l’image Nginx :

```powershell
docker compose up -d --build --wait
```

Puis ouvrir <http://localhost:8080/experience-art/index.html>. Le port dépend de `FRONTEND_PORT` si cette variable est déjà configurée. Le réseau externe `web` reste le prérequis habituel du socle ; voir le README général. Pour actualiser uniquement un frontend dont le socle est déjà démarré : `docker compose up -d --build --no-deps frontend`.

En développement :

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev -- --port 4173
```

Ouvrir <http://localhost:4173/experience-art/index.html>. Le nom `index.html` explicite fonctionne avec Vite et Nginx, sans ajouter de route Vue ni de middleware global. La galerie fonctionne sans API ni session et sans service distant. Le double-clic `file://` n’est pas le mode de lancement : la lecture du JSON passe par le serveur local. Les images restent consultables directement dans leurs dossiers.

La galerie permet de sélectionner chacun des huit chapitres, de regarder le master ou le premier plan seul sur un damier, de comparer les huit compositions, de consulter les dix éléments du storyboard et de lire la liste intégrale des ressources absentes. Les images sont statiques : aucun déplacement artificiel de photo ne sert de démonstration de caméra. Aucun bouton de lecture vidéo n’est affiché.

## Génération et traçabilité

Les images ont été produites avec l’outil intégré OpenAI `image_gen`, en mode natif. Aucune clé API n’a été demandée et aucun SDK ou générateur vidéo parallèle n’a été utilisé. Le nom du modèle n’est pas exposé par cet outil ; il n’est pas inventé dans le manifest.

Les masters sont générés à partir des consignes détaillées ; les premiers plans sont des éditions des masters avec demande explicite de transparence. Les prompts exacts sont conservés. Les fichiers sont copiés dans le dépôt ; aucune référence d’exploitation ne dépend du dossier privé de génération.

L’outil de vérification lit les dimensions PNG, la taille, l’empreinte SHA-256 et les valeurs alpha. Ces contrôles constatent une existence et une transparence ; ils ne valident ni une botanique, ni une géographie, ni un alignement de calques. Le détourage génératif peut conserver des franges ou modifier une feuille. La revue artistique de détail reste requise.

```powershell
cd frontend
npm.cmd run assets:refresh
npm.cmd run assets:check
npm.cmd run test -- art-assets
npm.cmd run test:e2e -- art-direction.spec.ts
```

`assets:refresh` actualise les métadonnées et les manifests de scènes à partir des fichiers réellement présents. Il ne génère ni image, ni vidéo, ne valide aucune approbation et refuse les fichiers absents annoncés comme présents. `assets:check` est en lecture seule et échoue en cas de dérive d’empreinte, ressource incohérente, alpha opaque ou logo modifié.

## Prompts manquants et formats

Chaque `prompts/missing.json` contient une consigne par ressource, sa résolution cible, son ratio, la focale, la lumière, le mouvement, la durée, les contraintes de continuité et le chemin attendu. Les entrées vidéo sont des briefs de pré-rendu pour Blender ou un outil de génération vidéo à sélectionner, **pas des commandes exécutées**.

Pour les fonds reconstruits : conserver l’optique et le point de vue du master, retirer uniquement les objets du premier plan et reconstruire ce qu’ils masquaient. La marge d’overscan doit être couverte. Pour les profondeurs : obtenir un champ 16 bits aligné et calibré avec les silhouettes. Pour les modèles : livrer la géométrie et les occlusions à la bonne échelle ; un prompt textuel ne les remplace pas.

Pour les séquences complexes : forêt→canopée, surface→immersion, déplacement autour du littoral. Livrer des plans de 4 à 8 secondes à 25 images/s, 1920 × 1080 au minimum, sans typographie ni inférence incrustées, avec poses de début/fin, focale, cadence, trajectoire et étalonnage documentés. Prévoir des images fixes correspondantes pour les mouvements réduits. Les séquences doivent être réversibles ou accompagnées d’une variante de retour ; une vidéo lue à rebours ne garantit pas un comportement physique plausible des reflets et des animaux.

La vidéo produit de 90 secondes est à capturer dans l’application réelle avec un jeu de données montrable et des sous-titres WebVTT. La capture de démonstration historique fournie dans le dépôt sert seulement de référence de langage graphique, pas d’enregistrement audiovisuel de substitution.

## Licences et provenance

L’inventaire autoritatif est `manifest.json`, sections `sources`, `licenses`, `exclusions` et champ `licenseId` de chaque ressource. Le logo et les références utilisateur ont des droits non précisés dans les sources inspectées ; aucune licence nouvelle ne leur est attribuée. Les rendus sont marqués comme générés avec l’outil OpenAI et soumis aux conditions du service et du compte, sans revendication CC ou exclusivité. Les ressources absentes n’ont aucun droit de diffusion acquis supposé.

L’[inventaire lisible des licences et provenances](PROVENANCE.md) récapitule les 16 fichiers produits. Un export CSV des 57 emplacements est disponible dans `output/symbiose/art-direction/asset-inventory.csv`.

Le site officiel de tourisme a servi à confirmer les noms des repères d’Étretat ; aucune photographie tierce n’est redistribuée. Les anciennes photographies du produit restent inchangées avec leurs crédits historiques. La nouvelle galerie ne récupère aucune image aléatoire sur Internet et ne présente aucune photo étrangère comme normande.

## Passage aux transitions

1. Valider les huit compositions, les capteurs illustratifs et le duo arche/Aiguille dans le film.
2. Reprendre les franges d’alpha et produire les fonds reconstruits et les profondeurs.
3. Contrôler géométrie, occlusions, trajectoires et continuité lumineuse.
4. Livrer et vérifier les plans pré-rendus nécessaires et la vidéo produit.
5. Mesurer le budget mémoire et la fluidité sur le matériel cible, puis seulement activer une transition.

Cette livraison s’arrête avant cette dernière phase. La configuration narrative exécutable du prototype et les pages métier restent séparées de la galerie.

Les commandes réellement exécutées, résultats et limites sont consignés dans [le rapport de validation](VALIDATION.md).
