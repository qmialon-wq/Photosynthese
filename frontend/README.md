# Symbiose — frontend et présentation du jury

Le frontend métier reste une application Vue 3 / TypeScript reliée à FastAPI.
La présentation du jury possède une entrée indépendante, `/jury/`, sans connexion,
appel métier ni modèle IA. Le logo et les huit milieux du parcours sont conservés.

## Lancer la production locale

Depuis la racine du dépôt, avec les services existants :

```powershell
docker compose up -d --build --no-deps frontend
```

- Application : `http://localhost:8080/` ; l'accueil connecté conserve son rôle.
- Présentation autonome : `http://localhost:8080/jury/`.
- Secours sans WebGL : `http://localhost:8080/jury/?render=2d`.

Pour présenter sans Docker ni backend, Node.js suffit après construction :

```powershell
cd frontend
npm.cmd ci
npm.cmd run build
node scripts/serve-jury.mjs dist
# http://localhost:8088/jury/
```

Le serveur fourni écoute uniquement sur `127.0.0.1`. Son second argument optionnel
permet de changer le port. Il sert les vidéos avec des réponses HTTP Range.

## Installer le mode hors ligne

Ouvrir `/jury/`, développer **Préparation du jury**, puis cliquer **Installer hors
ligne**. Attendre le message de réussite, puis tester un rechargement avec le
réseau coupé. Cette préparation exige une première lecture complète des fichiers
locaux. Le service worker est limité à `/jury/` ; il ne conserve ni session,
réponse API, document utilisateur, vidéo privée ou page métier.

L'installation et le point de reprise appartiennent au profil du navigateur et
à l'origine utilisée : `localhost`, `127.0.0.1` et un autre port sont différents.
Après une mise à jour installée, la page recharge la version cohérente du pack.
Garder le serveur local et le dossier de présentation comme secours.

Créer une copie portable contenant seulement les fichiers du jury :

```powershell
node scripts/package-jury.mjs
```

Le dossier versionné se trouve dans `output/symbiose/jury-package-<révision>/`.
Son README explique le lancement sans le dépôt.

## Vidéo et accès à Symbiose

Le montage produit de 90 secondes reste à fournir par l'équipe. Une capture du
manifeste le remplace explicitement. Déposer `public/experience-media/demo.mp4`
ou `demo.webm`, ajouter ses sous-titres WebVTT puis reconstruire et actualiser
l'installation. Le lecteur reste manuel et muet par défaut. Aucun faux parcours
produit n'est généré. Un fichier local peut aussi être ouvert sans téléversement ;
ce choix temporaire disparaît au rechargement.

Variables au build dans `frontend/.env.local` :

```dotenv
VITE_SYMBIOSE_APP_URL=http://localhost:8080/connexion
# Chemins locaux optionnels ; une configuration explicite absente fait échouer le build.
# VITE_SYMBIOSE_DEMO_URL=/experience-media/demo.mp4
# VITE_SYMBIOSE_DEMO_CAPTIONS_URL=/experience-media/demo.fr.vtt
```

L'accès final à l'application exige que l'application soit disponible ; son API,
les modèles et ses services ne sont pas inclus dans l'installation du pitch.

## Vérifier et reproduire les audits

```powershell
npm.cmd test
npm.cmd run build
node scripts/export-pitch.mjs --check
# Avec une production Nginx déjà active :
$env:E2E_BASE_URL = 'http://127.0.0.1:8080'
$env:E2E_PRODUCTION = '1'
npm.cmd run test:e2e -- narrative.spec.ts pitch.spec.ts jury.spec.ts logo-navigation.spec.ts authenticated-workspace.spec.ts
node scripts/audit-final.mjs --gpu
node scripts/audit-final.mjs
node scripts/audit-final.mjs --fallback
node scripts/audit-transitions.mjs --gpu
node scripts/audit-transitions.mjs --fallback
# Après création et lancement du pack sur 8088 :
node scripts/audit-jury-package.mjs
# Reconstruire les rapports depuis les métriques déjà mesurées :
node scripts/write-delivery-reports.mjs
```

Exécuter les audits de cadence séparément. Les rapports identifient le renderer
réel ; `--gpu` demande ANGLE D3D11 sous Windows sans supposer la présence d'une RTX.
Les captures et métriques sont dans `output/symbiose/final/`.

Les dérivés WebP sont déjà embarqués. Leur régénération facultative utilise
`scripts/requirements-assets.txt` (Pillow fixé), puis
`python scripts/optimize-experience.py`. Les masters et leurs preuves de
provenance restent intacts. Le manifest initial conserve ses 41 manques de
production et ses états de validation artistique.

Voir le [guide du présentateur](../docs/PRESENTER_GUIDE.md), le
[bilan de livraison](../docs/FINAL_DELIVERY.md) et le
[pitch chronométré](../docs/PITCH_DATATHON_2026.md).

Les [animaux et matériaux Poly Haven](../docs/SPATIAL_ASSETS.md) sont livrés dans
`public/experience-models/`, avec un inventaire d'empreintes. Leur préparation
utilise `python scripts/prepare-spatial-assets.py` ; les sources restent intactes.
Ajouter `spatial.spec.ts` aux scénarios Playwright pour contrôler les encadrés,
le retour arrière, la mémoire des squelettes et les GLB hors ligne.


## Reprise des décors

La nouvelle recette, les provenances, les limites et la régénération des arbres,
du bocage, des sols, de l'eau et des falaises sont dans
[SCENERY_REWORK.md](../docs/SCENERY_REWORK.md). La version servie par Nginx est
`31c94db9b955178c`. Les captures et mesures actuelles sont dans
`output/symbiose/scenery/` ; celles de `spatial/` documentent la version précédente.

Le pack portable mis à jour est `output/symbiose/Symbiose-jury-2026.zip`.
Le lancement et la procédure d'installation hors ligne sont identiques.
