import { readFile, mkdir, copyFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
const frontend = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
);
const dist = path.join(frontend, "dist");
const manifest = JSON.parse(
  await readFile(path.join(dist, "jury/offline-manifest.json"), "utf8"),
);
const destination = path.resolve(
  frontend,
  "../output/symbiose",
  `jury-package-${manifest.revision}`,
);
const files = [
  ...new Set([
    ...manifest.files.map((file) => file.url),
    "/jury/sw.js",
    "/jury/offline-manifest.json",
    "/experience-art/runtime-assets.json",
  ]),
];
for (const url of files) {
  const source = path.resolve(dist, "." + decodeURIComponent(url)),
    target = path.resolve(destination, "." + decodeURIComponent(url));
  if (
    !source.startsWith(dist + path.sep) ||
    !target.startsWith(destination + path.sep)
  )
    throw new Error("Invalid package path");
  await mkdir(path.dirname(target), { recursive: true });
  await copyFile(source, target);
}
await copyFile(
  path.join(frontend, "scripts/serve-jury.mjs"),
  path.join(destination, "serve-jury.mjs"),
);
await writeFile(
  path.join(destination, "README.md"),
  `# Symbiose · présentation locale du jury\n\nRévision : ${manifest.revision}.\n\nDepuis ce dossier, avec Node.js installé :\n\n\`\`\`powershell\nnode serve-jury.mjs .\n\`\`\`\n\nOuvrir http://localhost:8088/jury/. Dans « Préparation du jury », cliquer « Installer hors ligne » et attendre « Installation locale prête ». Tester un rechargement avec le réseau coupé dans le même profil de navigateur. Les autres pages de la plateforme et l’authentification ne sont pas incluses. Le CTA vise par défaut http://localhost:8080/connexion pour ce port de présentation ; configurer VITE_SYMBIOSE_APP_URL au build pour une autre installation.\n\n${manifest.demo.available ? "Vidéo locale incluse." : "La vidéo produit de 90 secondes est ABSENTE. Une capture du manifeste la remplace. Ce pack ne démontre pas le parcours produit complet."}\n\nRégie du récit : reprise du dernier chapitre, relance, passage d’animation et secours sans WebGL. L’URL /jury/?render=2d évite entièrement le GPU. Aucun son ne démarre automatiquement ; le lecteur est muet par défaut. Les photos de paysage sont des compositions générées, la 3D reste illustrative. La lecture des sources et le tableau du jury fonctionnent localement.\n\nLes octets de livraison et les empreintes sont dans jury/offline-manifest.json ; les dérivés d’images sont documentés dans experience-art/runtime-assets.json. Conserver le serveur local comme secours même après installation. Effacer les données du navigateur supprime l’installation et le point de reprise.\n`,
);
console.log(
  JSON.stringify(
    {
      destination,
      revision: manifest.revision,
      files: files.length,
      totalBytes: manifest.totalBytes,
      demo: manifest.demo,
    },
    null,
    2,
  ),
);
