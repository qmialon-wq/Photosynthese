# Démonstration locale Symbiose

`manifesto-review.png` est l'image embarquée de l'écran de validation humaine du
manifeste ARQ fourni par l'utilisateur, page 7 (objet PDF 41, 1907 × 895).
Elle est extraite sans retouche ; les nombres visibles sont ceux de la capture,
pas des résultats scientifiques annoncés par le pitch. Aucun droit ou partenariat
supplémentaire n'est déduit des logos présents dans le document.

La vidéo produit de 90 secondes n'est pas fournie. Ajouter `demo.mp4` ou
`demo.webm` ici puis reconstruire le frontend. MP4 est ignoré par le dépôt ;
la vidéo doit rester disponible dans le contexte de build local.
La sélection d'un fichier depuis la scène utilise une URL temporaire locale,
sans téléversement ni persistance. Il faut la refaire après rechargement.

Les chemins configurés dans `frontend/.env.local` remplacent les valeurs par
défaut au build Vite : `VITE_SYMBIOSE_APP_URL`, `VITE_SYMBIOSE_DEMO_URL` et
`VITE_SYMBIOSE_DEMO_CAPTIONS_URL` (WebVTT français). Les médias doivent être
servis par cette application, sans URL distante. Le lecteur ne se lance pas
automatiquement. Une durée en dehors de 85–95 secondes est signalée.

Les fichiers de test générés par Playwright ne sont pas des démonstrations produit.
