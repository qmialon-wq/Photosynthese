# Favicon adaptatif Symbiose — étape 18

## Fichiers officiels et préparation

Les deux symboles seuls fournis ont été copiés sans modification depuis les
téléchargements dans `frontend/src/assets/favicon/` :

| Source fournie                      | Copie conservée      | Dimensions  |
| ----------------------------------- | -------------------- | ----------- |
| `Datathon 2026 - Symbiose (10).png` | `symbiose-white.png` | 2006 × 2018 |
| `Datathon 2026 - Symbiose (11).png` | `symbiose-black.png` | 2010 × 2018 |

Aucun fichier vectoriel n'était disponible. Aucun tracé, texte ou slogan n'a été
ajouté. Le script `frontend/scripts/generate_favicons.py` retire les marges
transparentes des originaux, conserve leurs proportions, redimensionne avec
Lanczos et centre le symbole sur un carré transparent avec une marge de 1/16
de chaque côté. Les petites images ICO sont calculées directement à partir des
originaux haute résolution.

| Ressource dans `frontend/public/` | Utilisation                                 | Tailles intégrées  |
| --------------------------------- | ------------------------------------------- | ------------------ |
| `favicon-light.ico`               | Symbole noir, préférence navigateur claire  | 16, 32, 48, 256 px |
| `favicon-dark.ico`                | Symbole blanc, préférence navigateur sombre | 16, 32, 48, 256 px |
| `favicon.ico`                     | Secours sans condition, symbole noir        | 16, 32, 48 px      |
| `apple-touch-icon.png`            | Icône de raccourci Apple, symbole noir      | 180 px             |

Les variantes adaptatives sont multirésolutions : un PNG de 256 px seul pouvait
laisser Chrome privilégier les petites images exactes de l'ICO de secours. Ce
comportement a été constaté en suivant les requêtes du navigateur ; le mécanisme
de classement des tailles est décrit dans le
[code de Chromium](https://chromium.googlesource.com/chromium/src/+/lkgr/components/favicon/core/favicon_handler.cc).
Les PNG 16/32 px séparés et les SVG encapsulant du raster sont donc inutiles.

`frontend/index.html` déclare le secours en premier, puis les deux variantes avec
`media="(prefers-color-scheme: light)"` et `media="(prefers-color-scheme: dark)"`.
Les URL utilisent `%BASE_URL%`, remplacé par Vite. Ces déclarations sont communes
à toutes les routes, sans lien avec les paysages choisis dans Symbiose.

## Régénération et lancement

Depuis la racine du dépôt, pour régénérer les ressources uniquement :

```powershell
python -m pip install Pillow==11.1.0
python frontend/scripts/generate_favicons.py
```

Pillow sert uniquement à la préparation locale des fichiers. Les icônes générées
sont conservées dans le dépôt ; le démarrage et la compilation n'exécutent pas
ce script et ne nécessitent pas Python.

```powershell
cd frontend
npm run dev
```

Pour contrôler la version compilée, lancer dans un premier terminal :

```powershell
cd frontend
npm run build
npx vite preview --host 127.0.0.1 --port 4188 --strictPort
```

Puis dans un second terminal PowerShell :

```powershell
cd frontend
$env:E2E_BASE_URL = 'http://127.0.0.1:4188'
npx playwright test tests/e2e/favicon.spec.ts --browser=all
```

Si nécessaire, installer les moteurs avec `npx playwright install`.
Sans `E2E_BASE_URL`, Playwright utilise le serveur de développement configuré.

## Vérifications et limites

- `npm run build` : compilation TypeScript/Vite réussie ; les quatre ressources
  dans `dist/` sont identiques aux fichiers de `public/`.
- `npm test` : 114 tests unitaires réussis.
- Tests favicon : 9 réussis en développement et 9 sur la compilation, sur Chromium,
  Firefox et WebKit. Ils contrôlent les liens éligibles selon la préférence
  simulée, le rechargement, les tailles ICO, les couleurs et la transparence à
  16/32/48 px, les neuf rubriques et trois paysages. Les quatre ressources
  répondent HTTP 200 avec un type MIME image.
- Chrome installé, version 157.0.8103.52, dans un contexte neuf : observation
  des requêtes `favicon-light.ico` → `favicon-dark.ico` → `favicon-light.ico`
  au changement de préférence simulée, sans rechargement.
- Ruff et `git diff --check` réussis.
- Aperçu des images réellement intégrées aux ICO, taille native et zoom ×2 :
  [favicon-preview.png](../output/symbiose/etape-18/favicon-preview.png).

Les tests automatisés simulent la préférence système ; ils ne manipulent pas
les paramètres de Windows et n'inspectent pas le dessin de la barre d'onglets.
WebKit ne remplace pas un test de Safari natif, indisponible sur cet ordinateur
Windows. Contrôler sur macOS/iOS les onglets, favoris et raccourcis réels.
Les icônes déjà enregistrées peuvent conserver leur cache ou une copie fixe ;
vérifier dans un nouveau profil ou une fenêtre privée, puis recréer un ancien
favori/raccourci si nécessaire. L'icône Apple et le secours restent noirs ; leur
adaptation dynamique n'est pas garantie par les plateformes qui les enregistrent.
