# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: spatial.spec.ts >> supplied animals track their projected volumes, reverse deterministically and release skeletal GPU textures
- Location: tests\e2e\spatial.spec.ts:13:1

# Error details

```
Error: expect(received).toHaveLength(expected)

Expected length: 2
Received length: 0
Received array:  []
```

# Page snapshot

```yaml
- generic [ref=e2]:
  - link "Aller au récit" [ref=e3] [cursor=pointer]:
    - /url: "#main-content"
  - main [ref=e4]:
    - generic [ref=e5]:
      - generic [ref=e8]:
        - link "Symbiose Normandie — accueil" [ref=e9] [cursor=pointer]:
          - /url: /jury/
          - img "Symbiose" [ref=e10]
        - generic [ref=e11]:
          - text: UN PROJET NORMAND
          - generic [ref=e12]: Datathon Normandie · 2026
        - navigation "Navigation d’accueil" [ref=e13]:
          - button "Le projet" [ref=e14] [cursor=pointer]:
            - text: Le projet
            - generic [aria-hidden] [ref=e15]: +
          - link "Accéder à l’application" [ref=e16] [cursor=pointer]:
            - /url: /connexion
            - text: Accéder à l’application
            - generic [aria-hidden] [ref=e17]: ↗
      - generic [ref=e18]:
        - heading "Symbiose — Le vivant nous relie" [level=1] [ref=e19]
        - region "La vision" [ref=e20]:
          - paragraph [ref=e21]: LA VISION 0:35—1:00
          - heading "Un territoire. Des liens à comprendre." [level=2] [ref=e22]
          - paragraph [ref=e23]: Symbiose relie observations, connaissances et projets d’aménagement.
          - paragraph [ref=e24]: Fonction documentée
          - list [ref=e25]:
            - listitem [ref=e26]: Collectivités
            - listitem [ref=e27]: Agriculteurs et propriétaires
            - listitem [ref=e28]: Aménageurs et naturalistes
          - button "Sources et texte oral" [ref=e29] [cursor=pointer]: Sources et texte oral ↗
      - generic [ref=e30]:
        - generic [aria-hidden] [ref=e31]: ⌖
        - text: NORMANDIE, FRANCE
        - generic [ref=e33]: TRAJET ILLUSTRATIF · NON GÉOLOCALISÉ
      - generic [ref=e34]:
        - generic [ref=e35]: VOYAGE · 8 ATMOSPHÈRES
        - button "Reconstruction 3D · calques générés" [ref=e36] [cursor=pointer]: Reconstruction 3D · calques générés ↗
      - navigation "Environnements du voyage" [ref=e37]:
        - button "1. Forêt" [ref=e38] [cursor=pointer]:
          - generic [ref=e39]: "01"
          - generic: Le problème
        - button "2. Ciel et nuages" [active] [ref=e41] [cursor=pointer]:
          - generic [ref=e42]: "02"
          - generic [ref=e43]: La vision
        - button "3. Rivières" [ref=e45] [cursor=pointer]:
          - generic [ref=e46]: "03"
          - generic: Les données
        - button "4. Monde sous-marin" [ref=e48] [cursor=pointer]:
          - generic [ref=e49]: "04"
          - generic: Les perspectives
        - button "5. Zone humide" [ref=e51] [cursor=pointer]:
          - generic [ref=e52]: "05"
          - generic: Le moteur technique
        - button "6. Prairie et bocage" [ref=e54] [cursor=pointer]:
          - generic [ref=e55]: "06"
          - generic: La démonstration
        - button "7. Littoral — Étretat" [ref=e57] [cursor=pointer]:
          - generic [ref=e58]: "07"
          - generic: Les impacts
        - button "8. Forêt nocturne" [ref=e60] [cursor=pointer]:
          - generic [ref=e61]: "08"
          - generic: L’équipe et la suite
      - group "Commandes du pitch" [ref=e63]:
        - button "Chapitre précédent" [ref=e64] [cursor=pointer]: ← Précédent
        - button "Chapitre suivant" [ref=e65] [cursor=pointer]: Suivant →
        - button "Démonstration" [ref=e66] [cursor=pointer]: Démonstration ↗
        - button "Plein écran" [ref=e67] [cursor=pointer]
        - group [ref=e68]:
          - generic "Régie du récit" [ref=e69] [cursor=pointer]
      - generic [ref=e70]:
        - generic [ref=e71]: ← → chapitres · Espace lecture/pause · arrêt à chaque scène
        - generic [ref=e74]:
          - button "Lire le récit" [ref=e75] [cursor=pointer]: ▶
          - generic [ref=e76]:
            - generic [ref=e77]: Position dans le récit
            - slider "Position dans le récit" [ref=e78] [cursor=pointer]: "8.3"
          - generic [ref=e79]: 0:35 / 5:00
        - button "Mode présentation" [pressed] [ref=e80] [cursor=pointer]:
          - text: Mode présentation
          - generic [aria-hidden] [ref=e82]: ⇄
  - group [ref=e83]:
    - generic "Préparation du jury ○" [ref=e84] [cursor=pointer]
```

# Test source

```ts
  1  | import { expect, test, type Page } from "@playwright/test";
  2  | 
  3  | async function seek(page: Page, index: number, chapter: string) {
  4  |   await page.locator(".sx-chapter-nav button").nth(index).click();
  5  |   await expect(page.locator(".sx-pitch-content")).toHaveAttribute("data-chapter", chapter);
  6  |   await page.waitForFunction(() => {
  7  |     const state = document.querySelector<HTMLElement>(".sx-canvas")?.dataset.state;
  8  |     return state && !JSON.parse(state).assetsPending;
  9  |   });
  10 | }
  11 | const state = (page: Page) => page.locator(".sx-canvas").evaluate(el => JSON.parse((el as HTMLElement).dataset.state!));
  12 | 
  13 | test("supplied animals track their projected volumes, reverse deterministically and release skeletal GPU textures", async ({ page }) => {
  14 |   test.setTimeout(120000);
  15 |   await page.goto("/jury/");
  16 |   await expect(page.locator(".sx-stage")).toHaveClass(/sx-stage--ready/, { timeout: 45000 });
  17 |   const first = await state(page);
  18 |   expect(first.animals.map((a: any) => a.label)).toEqual(expect.arrayContaining(["Chevreuil", "Sanglier", "Pigeon"]));
  19 |   await seek(page, 1, "sky");
> 20 |   expect((await state(page)).animals.filter((a: any) => a.label === "Buse")).toHaveLength(2);
     |                                                                              ^ Error: expect(received).toHaveLength(expected)
  21 |   await seek(page, 3, "underwater");
  22 |   const submerged = await state(page);
  23 |   expect(submerged.animals).toHaveLength(3);
  24 |   expect(submerged.animals.every((a: any) => a.label === "Poisson · espèce à confirmer")).toBe(true);
  25 |   await seek(page, 4, "wetland");
  26 |   await seek(page, 7, "night-forest");
  27 |   await seek(page, 3, "underwater");
  28 |   const reverse = await state(page);
  29 |   expect(reverse.animals.map((a: any) => [a.id, a.x, a.y, a.width, a.height])).toEqual(submerged.animals.map((a: any) => [a.id, a.x, a.y, a.width, a.height]));
  30 |   await seek(page, 0, "forest");
  31 |   const returned = await state(page);
  32 |   expect(returned.textureCount).toBeLessThanOrEqual(first.textureCount + 2);
  33 |   const before = returned.renderCount;
  34 |   await page.waitForTimeout(500); // Idle observation, never an animation delay.
  35 |   expect((await state(page)).renderCount).toBeLessThanOrEqual(before + 1);
  36 | });
  37 | 
  38 | test("production offline installation includes the GLB models and PBR textures", async ({ page, context }) => {
  39 |   test.skip(!process.env.E2E_PRODUCTION, "Requires the emitted service worker");
  40 |   test.setTimeout(120000);
  41 |   const failed: string[] = [];
  42 |   page.on("requestfailed", request => { if (request.url().includes("experience-models")) failed.push(request.url()); });
  43 |   await page.goto("/jury/");
  44 |   await expect(page.locator(".sx-stage")).toHaveClass(/sx-stage--ready/, { timeout: 45000 });
  45 |   await page.locator(".jury-installation summary").click();
  46 |   await page.getByRole("button", { name: "Installer hors ligne", exact: true }).click();
  47 |   await expect(page.locator(".jury-installation [role=status]")).toContainText("Installation locale prête", { timeout: 65000 });
  48 |   await page.locator(".jury-installation summary").click();
  49 |   await context.setOffline(true);
  50 |   await page.reload();
  51 |   await expect(page.locator(".sx-stage")).toHaveClass(/sx-stage--ready/, { timeout: 45000 });
  52 |   await seek(page, 1, "sky");
  53 |   await expect(page.locator('.sx-animal-label').filter({ hasText: "Buse" })).toHaveCount(2);
  54 |   await seek(page, 3, "underwater");
  55 |   await expect(page.locator('.sx-animal-label').filter({ hasText: "Poisson" })).toHaveCount(3);
  56 |   expect(failed).toEqual([]);
  57 | });
  58 | 
```