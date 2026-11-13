import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
const root = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../..",
);
const read = async (file) =>
  JSON.parse(await readFile(path.join(root, file), "utf8"));
const report = (name) => read(`output/symbiose/final/${name}/report.json`);
const [baseline, gpu, software, fallback, transitions, assets, pack] =
  await Promise.all([
    report("baseline-gpu"),
    report("final-gpu"),
    report("final-software"),
    report("final-2d"),
    report("transitions/gpu"),
    read("frontend/public/experience-art/runtime-assets.json"),
    read("frontend/dist/jury/offline-manifest.json"),
  ]);
const rows = Object.entries(assets.scenes).flatMap(([scene, types]) =>
  Object.entries(types).map(([type, asset]) => ({ scene, type, ...asset })),
);
rows.push({ scene: "demo", type: "poster", ...assets.poster });
const original = rows.reduce((n, row) => n + row.sourceBytes, 0),
  delivered = rows.reduce((n, row) => n + row.bytes, 0);
const assetText = `# Symbiose — inventaire des assets

Inventaire du 13 novembre 2026. Les masters fournis restent intacts.
17 dérivés : **${original} → ${delivered} octets**, soit **${((1 - delivered / original) * 100).toFixed(2)} % de réduction**.
Ce total compare les mêmes images ; il ne mesure ni la mémoire GPU ni tout le dépôt.

| Milieu | Type | Dimensions | Source (octets) | Livraison (octets) |
|---|---|---|---:|---:|
${rows.map((a) => `| ${a.scene} | [${a.type}](../frontend/public${a.url}) | ${a.width} × ${a.height} | ${a.sourceBytes} | ${a.bytes} |`).join("\n")}

Les SHA-256, dimensions et réglages exacts sont dans [runtime-assets.json](../frontend/public/experience-art/runtime-assets.json).
Les tests vérifient ces empreintes et la copie incluse dans le bundle.

## Provenance et état

- Huit masters et huit premiers plans générés : provenance, licences et états d'approbation conservés dans le [manifest artistique](../frontend/public/experience-art/manifest.json). Les **41 ressources absentes** restent inventoriées. Les trois flags d'approbation restent faux.
- WebP Pillow **10.3.0**, qualité RGB 88 (poster 90), premiers plans réduits à 1280 px. Alpha identique à la résolution de livraison, RGB avec pertes. Aucun détail natif 4K revendiqué. Régénération avec les dépendances fixées dans "frontend/scripts/requirements-assets.txt".
- Logo blanc du produit exact, sans redessin ; bitmap du logo échantillonné en particules puis fermé. Ciel local et géométrie procédurale illustratifs.
- Poster : capture du manifeste ARQ, page 7, explicitement statique. Les extraits nécessaires aux sources du jury sont embarqués. Les anciennes photos du produit ne sont pas réétiquetées Normandie.
- Aucune police, texture ou vidéo distante indispensable. Les liens de bibliographie restent consultables, sans appel nécessaire au pitch.
- **Montage produit de 90 s et sous-titres absents.** Aucun film fictif ne les remplace. Codec, résolution, débit, cadrage et compression ne sont donc pas validés. À préparer avec l'équipe : lecture locale compatible Chromium, 1080p maximum si suffisant pour les détails de l'interface, débit ajusté visuellement et VTT français.

## Pack

Révision **${pack.revision}** : ${pack.files.length} ressources, **${pack.totalBytes} octets** dans le cache du jury.
Le manifeste "frontend/dist/jury/offline-manifest.json" liste chaque URL, poids et empreinte.
Le pack portable copie cette liste et ajoute le service worker, son manifeste, le serveur Node et son README.
Le total du cache ne comprend pas ces fichiers auxiliaires. Les PNG masters et la galerie de revue sont exclus.

Nginx compresse les textes, JS, CSS, JSON, SVG et VTT en gzip. WebP conserve sa compression propre.
Le serveur portable sert directement les fichiers et les requêtes Range, sans dépendance npm au lancement.
`;
const perfText = `# Symbiose — performance et sobriété

Mesures du 13 novembre 2026, **Chromium ${gpu.browser}**, Windows 11, **1440 × 900**.
CPU : ${gpu.cpu.trim()} ; RAM : ${(gpu.ramBytes / 1024 ** 3).toFixed(2)} Gio.
Renderer réel : "${gpu.scenes[0].state.renderer}".
**La RTX 3050 n'a pas servi à ces captures.**

## Protocole

Sept allers-retours de 3,5 s, avec 700 ms de démarrage exclues : cadence RAF et intervalles entre nouveaux rendus WebGL comptés séparément.
Une autre passe capture cinq états par raccord, revient en arrière et compare les pixels à 50 %.
Les délais de mesure ne pilotent aucune animation du site.
Les mesures de cadence sont exécutées séparément des builds et des autres audits navigateur.
Le PC reste celui de l'utilisateur, avec d'autres applications ouvertes : sa charge GPU et système n'est pas isolée.
Baseline et finale ne constituent donc **pas un benchmark contrôlé prouvant un gain de FPS**.
Les changements de cadrage et de décor modifient aussi la charge.

| Parcours | Baseline rendu (FPS) | Finale rendu (FPS) | P95 rendu final (ms) | Logiciel diagnostic (FPS) |
|---|---:|---:|---:|---:|
${gpu.measurements.map((m, i) => `| ${m.transition} | ${baseline.measurements[i].rendered.fps.toFixed(1)} | ${m.rendered.fps.toFixed(1)} | ${m.rendered.p95Ms.toFixed(1)} | ${software.measurements[i].rendered.fps.toFixed(1)} |`).join("\n")}

**60 FPS constants ne sont pas validés.** La finale atteint ponctuellement 60 FPS ; la seconde passe de raccords mesure ${Math.min(...transitions.performance.map((m) => m.renderedFps))}–${Math.max(...transitions.performance.map((m) => m.renderedFps))} rendus/s.
Le défaut intermédiaire d'une double programmation RAF à environ 30 FPS est corrigé : le rendu partage désormais l'horloge GSAP.
SwiftShader reste insuffisant même en éco (DPR 0,65 et végétation réduite).
La version livrée libère donc automatiquement les moteurs logiciels pour continuer en 2D.
Seul le paramètre diagnostique "?render=software" conserve ce moteur pour reproduire ses mesures.

## Chargement et ressources

- Scène prête : baseline **${baseline.startupMs} ms**, finale GPU **${gpu.startupMs} ms**, 2D **${fallback.startupMs} ms**. Mesures uniques, aucune amélioration de démarrage ni score Lighthouse revendiqué.
- Transfert cumulé du parcours public : **${baseline.transfer.bytes} → ${gpu.transfer.bytes} octets**, **${baseline.transfer.requests} → ${gpu.transfer.requests} requêtes**. Le chargement progressif répartit les requêtes. 2D : ${fallback.transfer.bytes} octets. Le bundle public inclut son contexte applicatif ; l'entrée jury évite l'authentification.
- Cache jury : **${pack.totalBytes} octets**, ${pack.files.length} ressources, vidéo absente. [Inventaire](FINAL_ASSETS.md).
- Scène immobile pendant 2,2 s : **${gpu.idleRenderDelta} nouveau rendu WebGL**.
- Sur huit poses : 2 à 4 images résidentes, jusqu'à 6 textures Three incluant la réfraction. Estimation maximale bitmaps + mipmaps : **19 660 800 octets**. Ce n'est pas une mesure de VRAM physique et cela exclut framebuffer, géométrie et allocations du pilote.
- Tas JS observé en fin de parcours : ${gpu.transfer.jsHeapBytes} octets (baseline ${baseline.transfer.jsHeapBytes}). Photographie ponctuelle, sans test d'endurance de plusieurs heures ni preuve d'absence de fuite.

| Pose | Draw calls baseline | Draw calls finale | Triangles finale |
|---|---:|---:|---:|
${gpu.scenes.map((s, i) => `| ${s.id} | ${baseline.scenes[i].state.drawCalls} | ${s.state.drawCalls} | ${s.state.triangles} |`).join("\n")}

Les draw calls ne diminuent pas partout : sous-bois et visibilité anticipée enrichissent certains plans.
Ce tableau ne démontre pas une réduction uniforme du coût de scène.

## Choix réellement implémentés

- WebP optimisés : **−87,14 %** sur 17 images, masters préservés ; alphas vérifiés à la taille livrée et RGB avec pertes.
- Ciel partagé et fenêtre de premiers plans voisins ; préchargement du suivant. Les cartes hors fenêtre, textures, matériaux, géométries et bitmaps sont libérés. Chargements dédupliqués, résultat obsolète protégé des textures encore attachées.
- Une passe sur terre, deux uniquement dans l'eau ; cible intermédiaire libérée à la sortie. Végétation instanciée ; éléments éloignés masqués ; détail de matière statique sans texture ni passe ajoutée.
- DPR standard plafonné à 1,5 ; éco initial à 0,65. Deux fenêtres lentes successives réduisent la résolution en standard. Logique testée ; aucune garantie de 60 FPS universels.
- Pas de rendu GPU autonome à l'arrêt, onglet caché ou carnet ouvert. Tous les effets suivent la progression narrative, sans horloge décorative infinie. Destruction au départ de la page.
- "prefers-reduced-motion" fixe les points de vue et désactive la lecture animée. Textes HTML, sources locales et navigation clavier restent disponibles. "?render=2d" évite entièrement le chargement et la création du contexte WebGL.
- Vidéo manuelle, "preload=none", muette au départ, pause au changement de chapitre et à l'ouverture des sources. Traitement du vrai montage absent encore à tester.
- Aucun CDN ni police distante indispensable. Gzip Nginx ; cache installé explicitement et limité au jury, sans cache de session ou de données métier.

Pas de mesure électrique, carbone, de temps GPU par timer query ou de VRAM physique effectuée.
Aucune économie énergétique chiffrée annoncée.

Rapports bruts : [baseline](../output/symbiose/final/baseline-gpu/report.json), [GPU](../output/symbiose/final/final-gpu/report.json), [logiciel](../output/symbiose/final/final-software/report.json), [2D](../output/symbiose/final/final-2d/report.json), [raccords GPU](../output/symbiose/final/transitions/gpu/report.json).
`;
await Promise.all([
  writeFile(path.join(root, "docs/FINAL_ASSETS.md"), assetText),
  writeFile(path.join(root, "docs/PERFORMANCE_SYMBIOSE.md"), perfText),
]);
console.log(
  "Inventaire et performance reconstruits depuis les rapports réels.",
);
