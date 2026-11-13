# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: pitch.spec.ts >> a real local media file stays manual, pauses for sources and releases on chapter departure
- Location: tests\e2e\pitch.spec.ts:233:1

# Error details

```
Error: expect(locator).not.toHaveAttribute() failed

Locator: locator('video')
Expected: not have attribute
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "not toHaveAttribute" locator('video') with timeout 5000ms
  - waiting for locator('video')

```

```yaml
- link "Aller au contenu":
  - /url: "#main-content"
- main:
  - paragraph: VERSION SIMPLIFIÉE 2D · IMAGES GÉNÉRÉES · MASQUE SPATIAL
  - link "Symbiose Normandie — accueil":
    - /url: /
    - img "Symbiose"
  - text: UN PROJET NORMAND Datathon Normandie · 2026
  - navigation "Navigation d’accueil":
    - button "Le projet"
    - link "Accéder à l’application":
      - /url: /connexion
  - heading "Symbiose — Le vivant nous relie" [level=1]
  - region "La démonstration":
    - paragraph: LA DÉMONSTRATION 2:30—4:00
    - heading "Du terrain à un dossier partagé." [level=2]
    - figure "SYMBIOSE / VALIDATION HUMAINE":
      - text: SYMBIOSE / VALIDATION HUMAINE 02:30–04:00 · DÉMO
      - img "Capture de l’écran de validation humaine Symbiose, extraite du manifeste ARQ, page 7. Données d’illustration, sans preuve de performance."
      - strong: La vraie interface. La vidéo reste à fournir.
      - text: Capture du manifeste · page 7 · remplacement statique test-signal.webm Choisir une vidéo locale
      - button "Choisir une vidéo locale"
      - status: Vidéo absente ou illisible. La capture du manifeste reste disponible.
  - text: NORMANDIE, FRANCE TRAJET ILLUSTRATIF · NON GÉOLOCALISÉ VOYAGE · 8 ATMOSPHÈRES
  - button "Version simplifiée 2D · images générées"
  - status:
    - paragraph: La vue WebGL n’est pas disponible. Le parcours est présenté en version 2D simplifiée.
    - button "Lire le projet et le parcours"
  - navigation "Environnements du voyage":
    - button "1. Forêt": 01 Le problème
    - button "2. Ciel et nuages": 02 La vision
    - button "3. Rivières": 03 Les données
    - button "4. Monde sous-marin": 04 Les perspectives
    - button "5. Zone humide": 05 Le moteur technique
    - button "6. Prairie et bocage": 06 La démonstration
    - button "7. Littoral — Étretat": 07 Les impacts
    - button "8. Forêt nocturne": 08 L’équipe et la suite
  - group "Commandes du pitch":
    - button "Chapitre précédent": ← Précédent
    - button "Chapitre suivant": Suivant →
    - button "Démonstration"
    - button "Plein écran"
    - group: Régie du récit
  - text: Défilez librement pour explorer Position dans le récit
  - slider "Position dans le récit": "63.1"
  - text: 06 / 08
  - button "Mode exploration"
```

# Test source

```ts
  152 |   await page.getByRole("button", { name: "Sources et texte oral" }).click();
  153 |   await expect(
  154 |     page.getByRole("heading", { name: /Les preuves, les mots/ }),
  155 |   ).toBeVisible();
  156 |   await expect(page.getByText(/Attendus vérifiés/)).toBeVisible();
  157 |   await page
  158 |     .getByRole("button", { name: "Attendus du jury", exact: true })
  159 |     .click();
  160 |   await expect(page.getByRole("table")).toBeVisible();
  161 |   await expect(page.getByRole("row")).toHaveCount(13);
  162 |   await page.getByRole("button", { name: "Pitch chronométré" }).click();
  163 |   await expect(page.locator(".sx-speaker-chapter")).toHaveCount(8);
  164 |   await page.getByRole("button", { name: "Fermer le projet" }).click();
  165 |   await cta.click();
  166 |   await expect(page).toHaveURL(/\/connexion$/);
  167 |   expect(external).toEqual([]);
  168 |   expect(errors).toEqual([]);
  169 | });
  170 | 
  171 | test("presentation keyboard, narrative stops, reverse navigation and reduced motion", async ({
  172 |   page,
  173 | }) => {
  174 |   await openPitch(page);
  175 |   await page.getByRole("button", { name: "Mode exploration" }).click();
  176 |   await page.locator("#main-content").focus();
  177 |   await page.keyboard.press("ArrowRight");
  178 |   await expect(page.locator(".sx-pitch-content")).toHaveAttribute(
  179 |     "data-chapter",
  180 |     "sky",
  181 |   );
  182 |   await expect(page.locator(".sx-counter")).toHaveText("0:35 / 5:00");
  183 |   await page.keyboard.press("ArrowLeft");
  184 |   await expect(page.locator(".sx-pitch-content")).toHaveAttribute(
  185 |     "data-chapter",
  186 |     "forest",
  187 |   );
  188 |   await page.keyboard.press("Space");
  189 |   await expect(
  190 |     page.getByRole("button", { name: "Mettre en pause", exact: true }),
  191 |   ).toBeVisible();
  192 |   await page.keyboard.press("Space");
  193 |   await expect(
  194 |     page.getByRole("button", { name: "Lire le récit", exact: true }),
  195 |   ).toBeVisible();
  196 |   // Start just before the first chapter boundary to check its actual automatic stop.
  197 |   await page.getByRole("slider").fill("8.2");
  198 |   await expect
  199 |     .poll(async () =>
  200 |       Number(
  201 |         await page.locator(".sx-experience").getAttribute("data-progress"),
  202 |       ),
  203 |     )
  204 |     .toBeCloseTo(0.082, 4);
  205 |   await page
  206 |     .getByRole("button", { name: "Lire le récit", exact: true })
  207 |     .click();
  208 |   await expect(page.locator(".sx-pitch-content")).toHaveAttribute(
  209 |     "data-chapter",
  210 |     "sky",
  211 |   );
  212 |   await expect(
  213 |     page.getByRole("button", { name: "Lire le récit", exact: true }),
  214 |   ).toBeVisible();
  215 |   await page
  216 |     .getByRole("button", { name: "Démonstration", exact: true })
  217 |     .click();
  218 |   await expect(page.locator(".sx-counter")).toHaveText("2:30 / 5:00");
  219 |   await expect(
  220 |     page.getByRole("button", { name: "Lire le récit" }),
  221 |   ).toBeDisabled();
  222 |   await page.emulateMedia({ reducedMotion: "reduce" });
  223 |   await expect(page.getByRole("button", { name: "Lire le récit" })).toHaveCount(
  224 |     0,
  225 |   );
  226 |   await page.locator("#main-content").focus();
  227 |   await page.keyboard.press("End");
  228 |   await expect(page.locator(".sx-counter")).toHaveText("5:00 / 5:00");
  229 |   await page.keyboard.press("Home");
  230 |   await expect(page.locator(".sx-counter")).toHaveText("0:00 / 5:00");
  231 | });
  232 | 
  233 | test("a real local media file stays manual, pauses for sources and releases on chapter departure", async ({
  234 |   page,
  235 | }) => {
  236 |   await openPitch(page);
  237 |   const bytes = await fixtureVideo(page);
  238 |   await page
  239 |     .getByRole("button", { name: "Démonstration", exact: true })
  240 |     .click();
  241 |   await expect(page.locator(".sx-pitch-content")).toHaveAttribute(
  242 |     "data-chapter",
  243 |     "meadow",
  244 |   );
  245 |   await page.locator('.sx-demo input[type="file"]').setInputFiles({
  246 |     name: "test-signal.webm",
  247 |     mimeType: "video/webm",
  248 |     buffer: bytes,
  249 |   });
  250 |   const video = page.locator("video");
  251 |   await expect(video).toHaveAttribute("controls", "");
> 252 |   await expect(video).not.toHaveAttribute("autoplay");
      |                           ^ Error: expect(locator).not.toHaveAttribute() failed
  253 |   expect(await video.evaluate((v: HTMLVideoElement) => v.paused)).toBe(true);
  254 |   await page
  255 |     .getByRole("button", { name: "Lancer la vidéo", exact: true })
  256 |     .click();
  257 |   await expect
  258 |     .poll(() => video.evaluate((v: HTMLVideoElement) => v.currentTime))
  259 |     .toBeGreaterThan(0.1);
  260 |   await page.getByRole("button", { name: "Mettre la vidéo en pause" }).click();
  261 |   expect(await video.evaluate((v: HTMLVideoElement) => v.paused)).toBe(true);
  262 |   await page
  263 |     .getByRole("button", { name: "Lancer la vidéo", exact: true })
  264 |     .click();
  265 |   await page.getByRole("button", { name: "Le projet", exact: true }).click();
  266 |   await expect(page.getByRole("dialog")).toBeVisible();
  267 |   expect(await video.evaluate((v: HTMLVideoElement) => v.paused)).toBe(true);
  268 |   await page.keyboard.press("Escape");
  269 |   expect(await video.evaluate((v: HTMLVideoElement) => v.paused)).toBe(true);
  270 |   const beforeWheel = Number(
  271 |     await page.locator(".sx-experience").getAttribute("data-progress"),
  272 |   );
  273 |   const videoBox = (await video.boundingBox())!;
  274 |   await page.mouse.move(
  275 |     videoBox.x + videoBox.width / 2,
  276 |     videoBox.y + videoBox.height / 2,
  277 |   );
  278 |   const panel = page.locator(".sx-pitch-content");
  279 |   expect(
  280 |     await panel.evaluate((el) => el.scrollHeight - el.clientHeight),
  281 |   ).toBeGreaterThan(0);
  282 |   await page.mouse.wheel(0, 100);
  283 |   await expect
  284 |     .poll(() => panel.evaluate((el) => el.scrollTop))
  285 |     .toBeGreaterThan(0);
  286 |   await expect(video).toBeVisible();
  287 |   expect(
  288 |     Number(await page.locator(".sx-experience").getAttribute("data-progress")),
  289 |   ).toBeCloseTo(beforeWheel, 6);
  290 |   // Once the pointer leaves the independently scrollable article, native page
  291 |   // scrolling must take control again without falling below the demo boundary.
  292 |   await page.mouse.move((await page.viewportSize())!.width - 8, 300);
  293 |   await page.mouse.wheel(0, 1000);
  294 |   await expect
  295 |     .poll(async () =>
  296 |       Number(
  297 |         await page.locator(".sx-experience").getAttribute("data-progress"),
  298 |       ),
  299 |     )
  300 |     .toBeGreaterThan(beforeWheel + 0.01);
  301 |   await page.getByRole("button", { name: "Chapitre suivant" }).click();
  302 |   await expect(video).toHaveCount(0);
  303 | });
  304 | 
  305 | test("mobile scenes and source book remain readable and accessible", async ({
  306 |   page,
  307 | }) => {
  308 |   await page.emulateMedia({ reducedMotion: "reduce" });
  309 |   await page.setViewportSize({ width: 390, height: 844 });
  310 |   await openPitch(page);
  311 |   for (const [name, id] of [
  312 |     ["1. Forêt", "forest"],
  313 |     ["5. Zone humide", "wetland"],
  314 |     ["6. Prairie et bocage", "meadow"],
  315 |     ["8. Forêt nocturne", "night-forest"],
  316 |   ]) {
  317 |     await chapter(page, name, id);
  318 |     await expect
  319 |       .poll(() =>
  320 |         page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
  321 |       )
  322 |       .toBe(true);
  323 |     expect(
  324 |       (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze())
  325 |         .violations,
  326 |     ).toEqual([]);
  327 |   }
  328 |   const finalAction = await page
  329 |     .getByRole("link", { name: "Commencer l’expérience Symbiose" })
  330 |     .boundingBox();
  331 |   const content = await page.locator(".sx-pitch-content").boundingBox();
  332 |   expect(finalAction!.y).toBeGreaterThanOrEqual(content!.y);
  333 |   expect(finalAction!.y + finalAction!.height).toBeLessThanOrEqual(
  334 |     content!.y + content!.height,
  335 |   );
  336 |   await page.screenshot({
  337 |     path: "../output/symbiose/pitch/mobile-conclusion.png",
  338 |   });
  339 |   await page.getByRole("button", { name: "Le projet", exact: true }).click();
  340 |   await expect(
  341 |     page.getByRole("heading", { name: /Les preuves, les mots/ }),
  342 |   ).toBeVisible();
  343 |   expect(
  344 |     (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze())
  345 |       .violations,
  346 |   ).toEqual([]);
  347 | });
  348 | 
  349 | test("unreadable local media and unavailable fullscreen have explicit fallbacks", async ({
  350 |   page,
  351 | }) => {
  352 |   await openPitch(page);
```