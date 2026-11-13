# Symbiose · présentation locale du jury

Révision : 3aeae4f97a928ea3.

Depuis ce dossier, avec Node.js installé :

```powershell
node serve-jury.mjs .
```

Ouvrir http://localhost:8088/jury/. Dans « Préparation du jury », cliquer « Installer hors ligne » et attendre « Installation locale prête ». Tester un rechargement avec le réseau coupé dans le même profil de navigateur. Les autres pages de la plateforme et l’authentification ne sont pas incluses. Le CTA vise par défaut http://localhost:8080/connexion pour ce port de présentation ; configurer VITE_SYMBIOSE_APP_URL au build pour une autre installation.

La vidéo produit de 90 secondes est ABSENTE. Une capture du manifeste la remplace. Ce pack ne démontre pas le parcours produit complet.

Régie du récit : reprise du dernier chapitre, relance, passage d’animation et secours sans WebGL. L’URL /jury/?render=2d évite entièrement le GPU. Aucun son ne démarre automatiquement ; le lecteur est muet par défaut. Les photos de paysage sont des compositions générées, la 3D reste illustrative. La lecture des sources et le tableau du jury fonctionnent localement.

Les octets de livraison et les empreintes sont dans jury/offline-manifest.json ; les dérivés d’images sont documentés dans experience-art/runtime-assets.json. Conserver le serveur local comme secours même après installation. Effacer les données du navigateur supprime l’installation et le point de reprise.
