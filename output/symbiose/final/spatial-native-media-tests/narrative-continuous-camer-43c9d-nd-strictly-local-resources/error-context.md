# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: narrative.spec.ts >> continuous camera, native wheel reversal, resize and strictly local resources
- Location: tests\e2e\narrative.spec.ts:30:1

# Error details

```
Test timeout of 30000ms exceeded.
```

# Page snapshot

```yaml
- generic [ref=e2]:
  - link "Aller au contenu" [ref=e4] [cursor=pointer]:
    - /url: "#main-content"
  - main [active] [ref=e5]:
    - generic [ref=e6]:
      - generic [ref=e9]:
        - link "Symbiose Normandie — accueil" [ref=e10] [cursor=pointer]:
          - /url: /
          - img "Symbiose" [ref=e11]
        - generic [ref=e12]:
          - text: UN PROJET NORMAND
          - generic [ref=e13]: Datathon Normandie · 2026
        - navigation "Navigation d’accueil" [ref=e14]:
          - button "Le projet" [ref=e15] [cursor=pointer]:
            - text: Le projet
            - generic [aria-hidden] [ref=e16]: +
          - link "Accéder à l’application" [ref=e17] [cursor=pointer]:
            - /url: /connexion
            - text: Accéder à l’application
            - generic [aria-hidden] [ref=e18]: ↗
      - generic [ref=e19]:
        - heading "Symbiose — Le vivant nous relie" [level=1] [ref=e20]
        - region "Le problème" [ref=e21]:
          - paragraph [ref=e22]: LE PROBLÈME 0:00—0:35
          - heading "Voir le vivant. Éclairer nos choix." [level=2] [ref=e23]
          - paragraph [ref=e24]: Des observations dispersées. Des projets à éclairer à l’échelle locale.
          - paragraph [ref=e25]: Bénéfice attendu · non mesuré
          - generic "Illustration d’une observation par caméra piège" [ref=e26]:
            - generic [ref=e29]: Caméra piège → observation à vérifier
            - generic [ref=e30]: Illustration · espèce et confiance non calculées
          - button "Découvrir la solution" [ref=e31] [cursor=pointer]:
            - text: Découvrir la solution
            - generic [aria-hidden] [ref=e32]: ↘
          - button "Sources et texte oral" [ref=e33] [cursor=pointer]: Sources et texte oral ↗
      - generic [ref=e34]:
        - generic [aria-hidden] [ref=e35]: ⌖
        - text: NORMANDIE, FRANCE
        - generic [ref=e37]: TRAJET ILLUSTRATIF · NON GÉOLOCALISÉ
      - generic [ref=e38]:
        - generic [ref=e39]: VOYAGE · 8 ATMOSPHÈRES
        - button "Reconstruction 3D · calques générés" [ref=e40] [cursor=pointer]: Reconstruction 3D · calques générés ↗
      - navigation "Environnements du voyage" [ref=e41]:
        - button "1. Forêt" [ref=e42] [cursor=pointer]:
          - generic [ref=e43]: "01"
          - generic: Le problème
        - button "2. Ciel et nuages" [ref=e45] [cursor=pointer]:
          - generic [ref=e46]: "02"
          - generic: La vision
        - button "3. Rivières" [ref=e48] [cursor=pointer]:
          - generic [ref=e49]: "03"
          - generic: Les données
        - button "4. Monde sous-marin" [ref=e51] [cursor=pointer]:
          - generic [ref=e52]: "04"
          - generic: Les perspectives
        - button "5. Zone humide" [ref=e54] [cursor=pointer]:
          - generic [ref=e55]: "05"
          - generic: Le moteur technique
        - button "6. Prairie et bocage" [ref=e57] [cursor=pointer]:
          - generic [ref=e58]: "06"
          - generic: La démonstration
        - button "7. Littoral — Étretat" [ref=e60] [cursor=pointer]:
          - generic [ref=e61]: "07"
          - generic: Les impacts
        - button "8. Forêt nocturne" [ref=e63] [cursor=pointer]:
          - generic [ref=e64]: "08"
          - generic: L’équipe et la suite
      - group "Commandes du pitch" [ref=e66]:
        - button "Chapitre précédent" [disabled] [ref=e67]: ← Précédent
        - button "Chapitre suivant" [ref=e68] [cursor=pointer]: Suivant →
        - button "Démonstration" [ref=e69] [cursor=pointer]: Démonstration ↗
        - button "Plein écran" [ref=e70] [cursor=pointer]
        - group [ref=e71]:
          - generic "Régie du récit" [ref=e72] [cursor=pointer]
      - generic [ref=e73]:
        - generic [ref=e74]: Défilez librement pour explorer
        - generic [ref=e77]:
          - generic [ref=e78]:
            - generic [ref=e79]: Position dans le récit
            - slider "Position dans le récit" [ref=e80] [cursor=pointer]: "4.2"
          - generic [ref=e81]: 01 / 08
        - button "Mode exploration" [ref=e82] [cursor=pointer]:
          - text: Mode exploration
          - generic [aria-hidden] [ref=e84]: ⇄
```