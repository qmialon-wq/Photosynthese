# SYMBIOSE — Cahier des charges V2 : aide à l’aménagement fondée sur ERC

**Échéance :** jeudi 12 novembre 2026, 12 h (heure de Paris)  
**Dépôt de référence :** `https://github.com/qmialon-wq/Photosynthese` — branche `main`, état examiné au commit `9fddb06beebac3be4a28da8a1ec84bb551b67fdc` (10 novembre).  
**Statut :** spécification, non développée. Ce document ne prétend pas que les fonctionnalités ci-dessous existent déjà.

## 1. Finalité et démonstration attendue

**Problématique :** comment exploiter l'IA et des données environnementales ouvertes pour comprendre les interactions entre activités humaines et biodiversité en Normandie et éclairer un projet d'aménagement ?

**Scénario MVP :** sur un dossier de parcelle existant, l'utilisateur sélectionne un point GPS, interroge les zonages officiels, consulte les faits cartographiques sourcés, les rapproche de son projet et des observations animales *humainement validées*, puis obtient des **questions à examiner / pistes d'adaptation**, sans décision automatique et sans score inventé.

**Définition du succès :** un **cas normand réel et reproductible** montrant le parcours `dossier → localisation → API IGN → faits vérifiés → questions et pistes → sources/export`. Une vidéo et une observation humaine confirmée doivent être intégrées à la recette complète lorsqu'elles sont disponibles ; sinon, préciser honnêtement la limitation dans la démonstration.

### Déjà présent dans Photosynthese — ne pas reconstruire

- FastAPI, Vue 3/TypeScript, PostgreSQL, Redis, workers, authentification et CSRF.
- Dossiers de parcelle / corpus de vidéos : `backend/app/parcels.py`, `shared/parcels/`, `frontend/src/pages/ParcelCorpusPage.vue`.
- Formulaire de parcelle : surface, type de terrain, projet, commune libre, détails (`shared/parcels/schemas.py`).
- Validation humaine et pipeline d'observations (`review`).
- Dossiers scientifiques et RAG (notamment `shared/parcels/report.py`, `docs/RAG.md`).
- Deux modes UI, **Démonstration** et **Données réelles** : ne jamais mélanger les résultats (`docs/DATA_MODES_SYMBIOSE.md`).
- Particularité : `/parcelles/:id` affiche `ParcelCorpusPage.vue` avec `readOnly=true`; `/admin/dossiers/:id` réutilise la même page. Les nouvelles opérations de localisation ne doivent pas débloquer les autres écritures existantes ni contourner les droits.

## 2. Périmètre P0 — obligatoire avant livraison

### P0.1 — Audit rapide et contrat de données

- Vérifier le HEAD, les modèles de parcelle, la dernière migration Alembic, les règles de propriété dans `backend/app/security.py`, le routage Vue et le worker documentaire.
- Créer une branche de fonctionnalité issue de `main`, sans modification de `main` pendant l'implémentation.
- Fixer un contrat JSON unique entre backend et frontend avant de travailler en parallèle.
- Identifier deux coordonnées de démonstration normandes provenant de cas réellement interrogés (au moins un résultat significatif si le service le permet), sans inventer de résultats.

**Acceptation :** plan court avec fichiers concernés, contrat JSON (incluant interventions, analyses ERC et sources) et liste des risques ; aucun code ou paramètre secret remplacé par inadvertance.

### P0.2 — Localisation persistante d'un dossier

- Enregistrer **latitude** et **longitude** WGS84 (EPSG:4326) d'un dossier de type `parcel_corpora`. Lors de la construction GeoJSON, respecter l'ordre **[longitude, latitude]**.
- Persister provenance de la saisie, acteur autorisé, date de mise à jour et révision ; une table distincte de localisation/consultation est préférable si cela évite de perturber les révisions historiques du formulaire.
- Saisie numérique + point sélectionnable sur une carte Leaflet, avec attribution du fond cartographique et prise en charge clavier de la saisie alternative.
- Ne pas afficher ce point comme le contour ou la surface réelle de la parcelle. La surface déclarée n'autorise pas à fabriquer un polygone.
- Lors d'un changement de coordonnées, marquer l'ancienne consultation comme **obsolète** ; ne jamais présenter une ancienne intersection comme concernant le nouveau point.

**Acceptation :** un utilisateur propriétaire enregistre un point, recharge la page et retrouve exactement sa localisation ; un autre client ne peut ni le lire ni le modifier ; coordonnées invalides rejetées.

### P0.3 — Connecteur open data IGN Nature

Service : `https://apicarto.ign.fr/api/nature` ; documentation `https://apicarto.ign.fr/api/doc/nature`.

Interroger **quatre couches**, séparément :

1. `znieff1`
2. `znieff2`
3. `natura-habitat`
4. `natura-oiseaux`

- Envoyer un Point GeoJSON en EPSG:4326 via les paramètres réellement documentés et vérifiés ; les réponses sont des `FeatureCollection` GeoJSON.
- Configurer une liste blanche de domaines/endpoints publics, timeouts bornés, erreurs HTTP, validation de schémas, limite de taille des réponses, retries limités et comportement d'indisponibilité.
- Normaliser chaque objet en : `layer`, `source_id`, `name`, `properties`, `geometry` (si exploitable), `source_url`, `retrieved_at`.
- Conserver pour chaque couche l'état `success`, `empty`, `unavailable` ou `error`, et au niveau global l'état `complete`, `partial`, `failed` ou `pending`.
- Sauvegarder le résultat et ses métadonnées, avec empreinte/identifiant de l'entrée et horodatage pour un audit reproductible. Conserver une vraie réponse publique archivée pour la démonstration de secours, **clairement identifiée comme archive**.
- Ne pas transformer une erreur réseau ou une réponse invalide en absence de zonage.
- Réutiliser les tâches Redis / worker documentaire si l'inspection confirme que c'est la voie la plus sûre. Ne pas lancer de traitement externe potentiellement long dans une requête HTTP ; la création de consultation doit renvoyer rapidement un identifiant et un statut.

**Acceptation :** deux points normands testés, retour normalisé avec sources, plus tests de réponse vide, erreur et indisponibilité. Aucun résultat cartographique fictif présenté comme réel.

### P0.4 — Moteur d’aide à l’aménagement (cadre ERC)

**Principe central :** partir des **interventions envisagées par l’humain**, et non d’un commentaire générique sur la biodiversité. Les faits sont calculés par du code déterministe ; les conseils sont **conditionnels**, liés à une intervention et à leurs preuves.

**Entrées** : point localisé et sa provenance ; couches IGN et états d’accès ; profil de parcelle ; projet déclaré ; *interventions projetées*, saisies par l’utilisateur ; observations `validated`/`corrected` réellement liées au dossier ; recommandations documentaires existantes si elles sont effectivement disponibles.

**Questionnaire d’interventions P0**, court et facultatif, sous forme de cases à cocher : `earthworks` (terrassement), `vegetation_removal` (suppression de haies/arbres), `fencing` (clôture), `outdoor_lighting` (éclairage extérieur), `soil_sealing` (imperméabilisation), `other` (description libre). Ne jamais considérer une case non cochée comme preuve de l’absence de travaux. Enregistrer les choix et leur révision sans effacer les historiques de dossiers.

**Sortie** d’un moteur déterministe indépendant du LLM :

- `facts[]` : faits vérifiés, identifiants et provenance (observation humaine, donnée cartographique, déclaration de l’utilisateur) ; toujours distinguer la catégorie de preuve.
- `project_concerns[]` : **quel élément précis du projet** mérite examen, déclencheur, raison, état des preuves et zone d’incertitude.
- `actions[]` : proposition structurée `avoid` (« Éviter »), `reduce` (« Réduire »), ou `investigate` (« Approfondir / vérifier »), avec `project_action`, texte conditionnel, `rationale`, `evidence_refs`, `preconditions`, `limitations`. Les deux premières sont des pistes d’adaptation, la troisième est une investigation, **pas une étape ERC**.
- `compensation` : `not_assessed` dans cette V1. Ne pas dimensionner ni recommander automatiquement de compensation, qui relève d’une étude des impacts résiduels et de compétences adaptées.
- `unknowns[]`, `limitations[]`, `sources[]` avec dates et identifiants.

**Exemples de règles métier P0 (ne jamais afficher comme constats un exemple non vérifié) :**

| Entrée déclenchante | Élément du projet examiné | Sortie admissible |
| --- | --- | --- |
| `fencing` déclaré + observation confirmée de faune terrestre sur les vidéos du dossier | Type et continuité de clôture | *Réduire* : examiner les besoins de passage de faune et, si l’usage et la sécurité le permettent, une clôture adaptée ; *approfondir* : vérifier les déplacements réels. Une vidéo ne démontre pas l’existence d’un corridor. |
| `outdoor_lighting` déclaré + source scientifique pertinente et vérifiée sur l’espèce ou le milieu | Emplacement, durée, intensité et orientation de l’éclairage | *Éviter / réduire* : étudier les alternatives sans éclairage, puis limiter l’éclairage nécessaire, **si étayé par une source pertinente** ; sinon classer comme question générale à documenter. |
| `vegetation_removal` déclaré + enjeux documentés (couche officielle et/ou étude scientifique pertinente) | Abattage / suppression de haies | *Éviter* : vérifier si une implantation alternative permet de conserver les éléments effectivement présents ; ne pas affirmer la présence d’une haie sans inventaire ou preuve. |
| `earthworks` ou `soil_sealing` déclaré + point intersectant un zonage officiel | Terrassement / emprise imperméabilisée | *Approfondir* : vérifier les habitats et l’emprise réelle ; *éviter* : envisager un autre emplacement si des enjeux sont confirmés. Le point ne représente pas la parcelle entière. |
| ZNIEFF/Natura 2000 sans interventions déclarées | Besoins d’instruction du projet | Questions contextualisées ; **aucun impact spécifique prétendument établi**. |
| Aucune intersection, source indisponible ou données seulement simulées | Tous travaux | Afficher un résultat explicitement limité ou indisponible ; ne pas déduire que le terrain est sans enjeu. |

**Règles scientifiques et juridiques obligatoires :**

1. L’intersection est prouvée **pour le point interrogé uniquement** ; aucune inférence d’emprise parcellaire ou de présence d’habitat n’est autorisée sans données supplémentaires.
2. Une espèce identifiée par l’IA mais non validée ne constitue pas une présence confirmée. Une observation confirmée ne prouve pas la reproduction, l’abondance, ni une fonction de corridor.
3. Une ZNIEFF est un inventaire écologique, pas une interdiction réglementaire automatique. Un zonage Natura 2000 n’entraîne pas par lui-même une conclusion juridique individualisée.
4. La démarche officielle est **Éviter → Réduire → Compenser** ; *Approfondir* est une **catégorie transverse de vérifications**, non la troisième étape. *Compenser* est **non évalué** dans ce MVP.
5. Différencier **constat**, **enjeu potentiel**, **piste conditionnelle**, **information manquante**, **qualification juridique non réalisée** dans les libellés et les exports.
6. Ne pas attribuer de « risque élevé / faible », de score chiffré, de pourcentage de terrain vert, ou de probabilité écologique sans méthode ou données validées.
7. Les références d’études RAG doivent être réelles et disponibles avant d’être utilisées pour justifier une mesure ; une citation bibliographique vérifiée ne garantit pas à elle seule l’applicabilité locale.
8. Si aucune source ne soutient une mesure spécifique, poser une question d’étude plutôt que générer une prescription.

**Intégration RAG P0 minimale :** ne pas attendre une génération longue. Afficher les faits territoriaux et les pistes conditionnelles **dans un encart déterministe** au dossier, avec leurs sources, à côté du rapport RAG existant. Si une intégration dans les quatre pages est simple et sûre, injecter un instantané de faits **non modifiables par le LLM** ; sinon, reporter cette réécriture en P1. Les données géographiques ne doivent jamais être inférées par le modèle.

**Acceptation P0 :** une même espèce et les mêmes couches conduisent à des pistes **différentes** selon que le projet mentionne clôture, éclairage ou terrassement ; au moins un cas sans source est traité comme information insuffisante ; tous les conseils conditionnels référencent leurs déclencheurs et limites ; tests déterministes des états de sources, espèces validées ou non, projet incomplet et changement de localisation. Pas de compensation automatique.

### P0.5 — UI et restitution sur la vraie donnée

- Ajouter la section **« Analyse préliminaire du projet »** (dont un volet **« Contexte territorial »**) à `ParcelCorpusPage.vue`, sans reconstruire le design system ni la roue Symbiose. Prévoir la saisie des interventions projetées et des explications conditionnelles.
- La page `/parcelles/:id` doit permettre au **propriétaire authentifié** de renseigner la localisation et demander l'enrichissement, via une nouvelle action expressément autorisée. Garder le formulaire historique en lecture seule là où il l'est déjà.
- En mode réel, interroger exclusivement le backend authentifié ; pas de remplacement par le scénario fictif. En mode démonstration, ne jamais transmettre les identifiants fictifs au backend.
- Afficher une véritable section **« Analyse préliminaire du projet »** : interventions déclarées, point cartographique, statuts des sources, **« Ce que nous savons »**, **« Ce que votre projet doit examiner »**, **« Éviter »**, **« Réduire »**, **« À vérifier »**, réserves et sources. Afficher **« Compenser : non évalué »** sans suggérer une compensation automatique. Fournir l'export JSON de l'analyse et de ses preuves.
- Protéger les écritures via les mécanismes existants de session, propriété, origine et CSRF. Mettre à jour les règles explicites dans `backend/app/security.py` pour les nouvelles routes, avec vérification serveur des permissions.

**Acceptation :** navigation `Mes dossiers → dossier → interventions du projet → carte → consultation IGN → analyse préliminaire ERC → résultat`, persistance et export JSON ; autre compte = refus ; source indisponible clairement affichée ; aucun résultat inventé en mode réel. Des actions **différentes** s’affichent pour des interventions différentes, si les preuves le justifient.

### P0.6 — Recette et preuve

- Appliquer la migration sur la base de développement sans réinitialiser les volumes.
- Exécuter les tests CPU unitaires, tests d'intégration PostgreSQL/Redis/API, build TypeScript/Vite et tests navigateur centrés sur le nouveau parcours.
- Effectuer au moins **une consultation IGN authentique**, conserver l'horodatage et les identifiants de couches renvoyés.
- Tester une instance connectée avec un dossier existant et, si disponible, une vidéo dont l'identification a été validée humainement. Documenter les éventuelles étapes non parcourues.
- Fournir `docs/TERRITORIAL_CONTEXT.md`, `docs/TERRITORIAL_VALIDATION.md`, captures et commande de lancement / tests ; inclure une explication des recommandations ERC, des déclencheurs et de leurs limites.
- Ne pas annoncer « tests réussis » pour une commande non exécutée.

**Acceptation :** compte rendu de recette honnête, preuve du flux réel, erreurs connues explicites et démonstration de secours distinguant archive et direct.

## 2 bis. Démonstration fonctionnelle à préparer

**Scénario illustratif ; faits environnementaux à confirmer par les données réelles au moment de la recette.** L’utilisateur souhaite construire une habitation. Il déclare une clôture, un éclairage nocturne et du terrassement. Une vidéo du dossier contient une observation de **blaireau humainement validée**, si ce cas existe réellement dans le corpus. Le point normand est interrogé via IGN ; la réponse peut indiquer une intersection réelle, aucune intersection ou une indisponibilité.

L’écran **« Analyse préliminaire du projet »** doit produire, dans cet ordre :

1. **Projet déclaré** : habitation ; clôture, éclairage, terrassement.
2. **Constats vérifiés** : observation humaine avec source ; résultats IGN du point, couches, nom du site s’il existe et date.
3. **Ce que ces constats ne prouvent pas** : ni couloir de déplacement sur la parcelle, ni habitat précis, ni emprise réelle des travaux.
4. **Éviter** : explorer, **sous réserve d’enjeu écologique confirmé**, une implantation qui préserve les éléments sensibles réellement identifiés ; se demander si un éclairage est indispensable.
5. **Réduire** : examiner l’adaptation de la clôture et de l’éclairage **si** les sources applicables justifient ces pistes et selon les contraintes du projet.
6. **Approfondir** : vérifier les déplacements de la faune, l’implantation et les habitats sur le terrain ; déterminer si un spécialiste doit intervenir.
7. **Compenser** : « Non évalué. La compensation intervient éventuellement après qualification des impacts résiduels dans une démarche adaptée. »
8. **Sources et réserves** visibles et exportables, sans affirmation sur un zonage ou une espèce qui ne figure pas réellement dans les résultats.

Le jury doit comprendre en moins d’une minute **quelle caractéristique concrète du projet pourrait être revue, pourquoi, et ce qui reste à vérifier**.

## 3. P1 — uniquement après validation intégrale du P0

**P1-A — Enrichir la Normandie avec les zones humides.** Tester et, si faisable, exploiter le jeu officiel DREAL « Zones Humides - Normandie » (licence ouverte), source : `https://www.data.gouv.fr/datasets/zones-humides-normandie`. Distinguer une zone inventoriée d'un milieu seulement *prédisposé* à être humide, et préciser la méthode/échelle et l'incertitude de la donnée. Priorité à un extrait géographique restreint ou à WFS. Ne pas télécharger toute la Normandie sans justification.

**P1-B — Intégration rédactionnelle approfondie dans le RAG.** Après la restitution ERC P0 en encart déterministe, intégrer éventuellement les faits contrôlés dans les quatre pages rédigées, sans modifier les preuves. Ne pas rallonger la génération au détriment de la recette.

**P1-C — Comparaison de variantes.** Seulement si le reste est stable : comparer deux points d'implantation, sans les transformer en polygones ni déclarer automatiquement un gagnant. Si le temps manque, reporter explicitement.

**Hors périmètre :** nouveaux entraînements ML, nouvel outil cartographique complet, scores de risque arbitraires, simulation de populations animales, inventaire exhaustif régional, décision juridique automatique, refonte des six pages.

## 4. Proposition de contrat HTTP / JSON (à ajuster après audit)

| Méthode et route | Usage |
|---|---|
| `PUT /parcels/corpora/{id}/location` | Saisir/modifier le point et sa provenance |
| `POST /parcels/corpora/{id}/territorial-queries` | Lancer une consultation asynchrone, retourner `query_id` et `status` |
| `GET /parcels/corpora/{id}/territorial-context` | Obtenir la dernière consultation, son statut, ses sources et synthèses |
| `GET /parcels/corpora/{id}/territorial-context/export` | Télécharger l'instantané JSON sourcé |

Structure indicative de la réponse :

```json
{
  "location": {"latitude": null, "longitude": null, "geometry_type": "Point", "source": "user"},
  "query": {"id": null, "status": "pending", "queried_at": null, "stale": false},
  "layers": [
    {"code": "znieff1", "status": "pending", "features": [], "source_url": "https://apicarto.ign.fr/api/doc/nature"}
  ],
  "project_interventions": ["fencing", "outdoor_lighting"],
  "facts": [],
  "project_concerns": [],
  "actions": [],
  "compensation": {"status": "not_assessed"},
  "unknowns": [],
  "limitations": [],
  "sources": []
}
```

Ce JSON illustre **le contrat uniquement**, pas une réponse environnementale réelle. Définir les modèles Pydantic/TypeScript partagés avant toute implémentation UI.

## 5. Ordre d'exécution et règles de collaboration Codex

**Mardi 10 novembre :** audit et contrat → localisation + projet/interventions → IGN et persistance → premières règles ERC liées aux interventions → un test réel.

**Mercredi 11 novembre :** écran « Analyse préliminaire du projet » → intégration avec les dossiers et le RAG existant (encart déterministe) → recette API + PostgreSQL/Redis → test navigateur → export et documentation → gel des nouvelles fonctionnalités. P1 uniquement si P0 terminé.

**Jeudi 12 novembre, avant 12 h :** vérification et livraison ; pas de refonte ou de nouveau chantier.

Codex peut paralléliser **backend** et **frontend** après validation du contrat. Utiliser des branches/worktrees distincts si plusieurs agents touchent au dépôt ; un seul intégrateur réalise les fusions. Préserver les fichiers existants et éviter les commits massifs sans tests. Ne jamais lancer de commande destructive (`git reset --hard`, suppression de volumes ou données) sans autorisation.

### Rapport final exigé de Codex

1. Ce qui est **implémenté et validé** (pas seulement prévu).
2. Fichiers/migrations/routes modifiés et architecture retenue.
3. Tests réellement exécutés avec résultats et limites de couverture.
4. Démonstration pas à pas sur une vraie donnée IGN et un dossier accessible.
5. Sources publiques utilisées, dates d'interrogation et limites scientifiques.
6. Chantiers P1 reportés et blocages restants.

## 6. Références officielles

- IGN API Carto Nature : https://apicarto.ign.fr/api/doc/nature
- Principes de l'API Carto : https://apicarto.ign.fr/api/doc/
- Open data DREAL Normandie, zones humides : https://www.data.gouv.fr/datasets/zones-humides-normandie
- Parcours technique du dépôt : https://github.com/qmialon-wq/Photosynthese/blob/main/docs/PARCEL_DOSSIERS.md
- Conception des deux modes : https://github.com/qmialon-wq/Photosynthese/blob/main/docs/DATA_MODES_SYMBIOSE.md
- RAG existant : https://github.com/qmialon-wq/Photosynthese/blob/main/docs/RAG.md
- Doctrine ERC — Ministère : https://www.ecologie.gouv.fr/politiques-publiques/eviter-reduire-compenser-impacts-lenvironnement
- OFB — mise en œuvre ERC : https://ofb.gouv.fr/des-outils-pour-mettre-en-oeuvre-la-sequence-eviter-reduire-compenser-erc

---

**Critère de stop :** si une fonctionnalité P0 reste instable mercredi soir, ne pas commencer P1. Conserver la démonstration du dernier parcours réel validé et documenter l'élément incomplet.
