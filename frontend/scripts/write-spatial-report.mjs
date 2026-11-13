import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const read = async file => JSON.parse(await readFile(path.join(root, file), "utf8"));
const [gpu, previous, manifest, unit, cache, firstTests, release, portable, transitions] = await Promise.all([
  read("output/symbiose/spatial/release-gpu/report.json"),
  read("output/symbiose/spatial/before-cache-report.json"),
  read("frontend/dist/jury/offline-manifest.json"),
  read("output/symbiose/spatial/tests-unit.json"),
  read("output/symbiose/spatial/tests-unit-cache.json"),
  read("output/symbiose/spatial/tests-production.json"),
  read("output/symbiose/spatial/tests-release.json"),
  read("output/symbiose/final/package/report.json"),
  read("output/symbiose/spatial/transitions/gpu/report.json"),
]);
const performance = `# Symbiose — performance après intégration 3D

Production du 13 novembre 2026, révision **${manifest.revision}**.
Mesure réelle : Chromium ${gpu.browser}, Windows, ${gpu.cpu.trim()}, ${(gpu.ramBytes / 1024 ** 3).toFixed(2)} Gio RAM.
Viewport 1440 × 900, renderer **${gpu.scenes[0].state.renderer}**.
Il s'agit de l'AMD intégré ; la RTX 3050 n'est pas utilisée dans cette mesure.

| Raccord | Cadence de nouveaux rendus (FPS) | P95 entre rendus (ms) | Draw calls en fin d'échantillon |
|---|---:|---:|---:|
${gpu.measurements.map(m => `| ${m.transition} | ${m.rendered.fps.toFixed(1)} | ${m.rendered.p95Ms.toFixed(1)} | ${m.finalState.drawCalls} |`).join("\n")}

Protocole : sept allers-retours de 3,5 s, 700 ms de mise en mouvement exclues, mesures exécutées séparément des builds et des autres navigateurs de test.
Le PC n'est pas isolé des autres applications : ce n'est pas un benchmark contrôlé.
**60 FPS constants ne sont pas validés.** Les résultats ne sont pas extrapolés à d'autres GPU ni à la salle de projection.
Une seconde passe par les contrôles debug des raccords mesure **${Math.min(...transitions.performance.map(m => m.renderedFps))}–${Math.max(...transitions.performance.map(m => m.renderedFps))} rendus/s**. Les deux protocoles et les variations de charge du PC doivent rester visibles dans l'interprétation ; la première plage ne constitue pas une cadence garantie.

- Scène prête en **${gpu.startupMs} ms**, observation unique.
- Sur 2,2 s immobiles : **${gpu.idleRenderDelta} nouveau rendu WebGL**.
- Parcours complet de capture et d'aller-retour : **${previous.transfer.bytes} → ${gpu.transfer.bytes} octets transférés**, **${previous.transfer.requests} → ${gpu.transfer.requests} requêtes**, avant/après le cache des GLB encodés. Le parcours inclut des passages répétés ; ces chiffres ne décrivent pas seulement le premier chargement.
- Cache hors ligne installé : **${manifest.totalBytes} octets**, **${manifest.files.length} ressources**, vidéo produit absente. Serveur et README sont supplémentaires au cache.
- Tas JS observé à la fin : **${gpu.transfer.jsHeapBytes} octets**. Ce compteur ne comprend pas toutes les allocations natives, buffers ou textures du pilote.
  Avant le cache, la photographie correspondante était de ${previous.transfer.jsHeapBytes} octets. Le cache échange une rétention CPU bornée contre des transferts évités ; les deux photographies n'ont pas un cycle de GC contrôlé et ne prouvent pas un gain de mémoire.

| Pose | Draw calls | Triangles | Textures Three | Animaux encadrés visibles |
|---|---:|---:|---:|---:|
${gpu.scenes.map(s => `| ${s.id} | ${s.state.drawCalls} | ${s.state.triangles} | ${s.state.textureCount} | ${s.state.animals?.length || 0} |`).join("\n")}

Les textures décomptées incluent celles des GLB, matériaux et squelettes. Le champ estimatedImageBytes de la télémétrie porte seulement sur les images du préchargeur historique ; il ne représente pas tout le nouveau décor.
**Aucune mesure de VRAM physique, d'énergie ou d'émissions carbone n'a été effectuée.**
Le contrôle de retour à la forêt teste la libération des textures de squelette après plusieurs changements de milieu ; ce n'est pas un test d'endurance de plusieurs heures.

Les stratégies mises en œuvre sont décrites dans [Animaux et matières](SPATIAL_ASSETS.md) : copies 1K, regroupement du rapace, instanciation et secteurs, chargement anticipé, éviction des objets décodés, cache compressé borné, destruction à l'arrêt, DPR adaptatif et repli 2D.
Le diagnostic logiciel antérieur mesurait moins de 10 FPS ; ce moteur bascule donc automatiquement vers la 2D.

[Rapport brut](../output/symbiose/spatial/release-gpu/report.json) · [captures des huit chapitres](../output/symbiose/spatial/release-gpu/index.html).
`;
const tests = `# Symbiose — rapport des tests exécutés

Recette locale du 13 novembre 2026. Production finale : **${manifest.revision}**, Nginx sur 8080, pack autonome sur 8088.
Le build TypeScript/Vite a été exécuté localement et dans Docker. Seul le frontend a été reconstruit.
L'avertissement de chunk Three supérieur à 500 ko reste présent ; ce chunk est chargé à la demande et évité par la 2D forcée.

## Exécutions réelles

| Exécution | Résultat |
|---|---|
| Suite Vitest, 28 fichiers, deux workers et timeout 15 s | ${unit.numPassedTests}/${unit.numTotalTests} réussis, ${unit.numFailedTests} échec |
| Contrôles ciblés du cache GLB et des assets/encadrés/particules | ${cache.numPassedTests}/${cache.numTotalTests} réussis |
| Première recette complète, 34 scénarios | ${firstTests.stats.expected} réussis, ${firstTests.stats.unexpected} échecs ; deux nouveaux tests visaient le début du chapitre avant l'arrivée des animaux |
| Recette finale des scénarios concernés après cache et correction des poses de test | ${release.stats.expected} réussis, ${release.stats.unexpected} échecs, ${release.stats.skipped} ignoré, ${release.stats.flaky} instable |
| Pack autonome final | Rechargement hors ligne : ${portable.offlineReload} ; huit chapitres ; sources locales ; plein écran natif Chromium : ${portable.fullscreen} ; sortie du plein écran ; redimensionnement ; lien réel vers ${portable.applicationReached} |
| Audit visuel/métriques de production, huit chapitres et sept allers-retours | ${gpu.errors.length} erreur JavaScript ; ${gpu.external.length} requête externe |
| Raccords actuels avec les animaux | ${transitions.records.length * 5} poses capturées ; ${transitions.records.filter(r => r.replayComparison.withinTolerance).length}/${transitions.records.length} rejeux dans la tolérance ; ${transitions.records.filter(r => r.replayPixelIdentical).length} strictement identique ; ${transitions.errors.length} erreur |
| Préparation Python | Exécution réelle du convertisseur, contrôle des SHA-256, compilation Python et Ruff 0.9.10 check/format exécutés |

La première recette complète et la dernière recette ciblée sont deux exécutions distinctes : aucune commande unique de 34 scénarios n'est annoncée entièrement verte. Les 32 scénarios existants étaient verts avant la dernière optimisation du cache. La recette ciblée reprend le récit, la vidéo, le jury et les deux scénarios 3D ajoutés.

## Périmètre des dix vérifications demandées

| Vérification | Ce qui a réellement été exécuté |
|---|---|
| Démarrage | Entrée publique et entrée jury ; absence d'appel métier dans le jury ; erreur WebGL et bascule logicielle vers 2D |
| Scroll complet | Parcours des huit chapitres par progression contrôlée et positions représentatives, sept allers-retours instrumentés ; molette native dans des scénarios séparés |
| Retour arrière | Molette, navigation de chapitre, poses réversibles et encadrés aux mêmes positions ; nouveaux GLB rechargés après éviction |
| Clavier | Flèches, Page précédente/suivante, Début/Fin, Espace, Tab, Échap, focus du carnet ; touches natives conservées sur le lecteur et les formulaires |
| Vidéo | Fichier VP8 local de test réellement décodé et lu, contrôles manuels, pause, carnet, molette du panneau interne, libération au départ ; erreur d'un fichier illisible |
| Plein écran | Entrée et sortie natives dans Chromium sur le pack autonome ; scénario de refus de l'API également testé |
| Redimensionnement | Plusieurs viewports desktop ; conservation de position ; mobile simulé 390 × 844, sans appareil mobile physique |
| Exploration | Défilement natif et interruption de lecture ; aucune boucle GPU à l'arrêt |
| Présentation | Arrêts, navigation immédiate, passage d'animation, reprise après rechargement et relance |
| Lien final | Attribut attendu, clic réel vers la page de connexion de l'application disponible sur 8080 |

Les scénarios métier utilisent des réponses API/session de test ; ils ne prouvent pas une inférence GPU ni une analyse écologique. Le signal vidéo validé est dans tests/fixtures et n'est jamais embarqué comme démonstration du produit.
Les contrôles Axe exécutés portent sur les états desktop/mobile/carnet couverts ; ils ne constituent pas une certification WCAG complète.

## Incidents corrigés ou distingués

- Transition DOM laissant un texte momentanément absent, cadrage trop haut du poster et programmation à 30 FPS : corrigés avant les captures finales.
- Molette interne pouvant perdre la frontière exacte du chapitre vidéo : corrigée, puis testée avec un vrai fichier décodable.
- Génération vidéo MediaRecorder instable dans le test : remplacée par un fichier VP8 local dont la lecture a été contrôlée séparément, sans changer le produit pour faire passer le test.
- Un contrôle unitaire attendait encore les anciens poissons en cônes : il vérifie désormais leur remplacement et le fondu des bulles ; les vrais poissons sont contrôlés en navigateur.
- Un timeout de 5 s lors du contrôle des PNG sous forte charge : suite rejouée avec deux workers et 15 s. Le résultat final est celui indiqué plus haut.
- Un ancien lancement concurrent de deux runners partageant leur dossier d'artefacts a produit une erreur de trace ; les recettes de livraison utilisent des dossiers distincts et un seul worker.

## Non exécuté / limites

Véritable montage produit de 90 s et ses VTT absents ; vrai SVG du logo absent ; validation naturaliste des modèles ; vidéoprojecteur ; Firefox/Safari ; lecteur d'écran humain ; appareil mobile physique ; campagne multi-GPU ; endurance de plusieurs heures ; mesure de VRAM ou d'énergie ; inférence métier réelle dans le pack.
Les captures de raccords historiques précèdent les modèles ; une nouvelle passe de 35 poses et sept rejeux les inclut. Les comparaisons acceptent au maximum 8 niveaux par canal et 0,01 % de pixels modifiés. Elles ne prouvent pas l'absence de tout saut perceptible entre deux états échantillonnés. La galerie courante de chapitres montre également les animaux ; les rapports bruts identifient chaque exécution et ne doivent pas être mélangés.

## Preuves

[Unitaires](../output/symbiose/spatial/tests-unit.json), [cache ciblé](../output/symbiose/spatial/tests-unit-cache.json), [recette complète](../output/symbiose/spatial/tests-production.json), [recette finale ciblée](../output/symbiose/spatial/tests-release.json), [pack](../output/symbiose/final/package/report.json), [captures actuelles](../output/symbiose/spatial/release-gpu/index.html), [35 poses des raccords](../output/symbiose/spatial/transitions/gpu/index.html).
`;
await Promise.all([
  writeFile(path.join(root, "docs/SPATIAL_PERFORMANCE.md"), performance),
  writeFile(path.join(root, "docs/FINAL_TEST_REPORT.md"), tests),
]);
console.log("Rapports spatiaux reconstruits à partir des exécutions enregistrées.");
