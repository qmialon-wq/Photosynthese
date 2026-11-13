# Symbiose — pitch du Datathon Normandie 2026

Généré depuis [pitch.ts](../frontend/src/experience/pitch.ts) par `node frontend/scripts/export-pitch.mjs`.

Durée cible : **5 minutes**, dont **90 secondes** de démonstration manuelle. Le texte hors vidéo compte environ **392 mots**, soit **112 mots/minute** sur 3 min 30. C’est une estimation éditoriale : une répétition avec les transitions et les pauses reste nécessaire.

## État des sources et limites

Le manifeste final ARQ (13 pages, dont les captures), le règlement fourni (5 pages), la trame de descriptif DOCX (vierge), l’image des cinq questions, les guides du dépôt, les recettes techniques et les archives territoriales ont été examinés. Le manifeste répond aux sept rubriques de la trame : solution et équipe, mots-clés, problème, cibles, bénéfices attendus, producteurs et liens des données, accès et captures. Les sources externes mentionnées sont celles utilisées par le code ; aucune actualisation réseau n’est réalisée par cette présentation. Le règlement § 5, p. 3 donne six critères : pertinence thématique, originalité, innovation, sobriété numérique, faisabilité et qualité orale. L’image fournie fixe les cinq questions. La correspondance ci-dessous les couvre sans prétendre certifier l’ensemble des obligations administratives du concours. Le § 3 du règlement mentionne emploi-formation et cite les données de biodiversité dans sa note de bas de page ; cette ambiguïté du document n’est pas réécrite. La vidéo produit de 90 secondes sera réalisée en aval par l’équipe. Le remplacement est une capture de validation humaine extraite du manifeste, page 7, et non une vidéo ou une preuve de performance. Les vidéos de navigation archivées et la vidéo d’écureuil ne remplacent pas une démonstration produit.

Les douze options de conception sont un inventaire fonctionnel documenté ; aucun gain écologique, gain de temps ou score de reconnaissance validé n’est annoncé. Les observations animales de la recette territoriale sont synthétiques. Les besoins de passage à l’échelle sont des propositions éditoriales à confirmer par l’équipe, sans partenaire acquis ni montant inventé.

## Déroulé chronométré

### 0:00–0:35 · Le problème (35 s)

**Message principal :** Des observations dispersées. Des projets à éclairer à l’échelle locale.

**Statut :** Bénéfice attendu · non mesuré.

**Texte oral proposé :** Une caméra piège filme un animal. Mais comment passer de cette observation à une décision d’aménagement ? Les vidéos, les inventaires et les études existent ; ils restent dispersés et longs à analyser. Pour une collectivité, un agriculteur ou un aménageur, connaître les enjeux locaux reste difficile. Symbiose veut relier ces informations pour éclairer les choix, avant les travaux.

**Écran :** Voir le vivant. Éclairer nos choix. — Observer ; Comprendre ; Préparer la décision.

**Interaction / animation :** Une caméra piège et une silhouette animale illustrent une observation candidate, sans score inventé.

**Transition :** La caméra quitte le sous-bois et prend de la hauteur.

**Sources locales :** manifesto, description, jury-questions (voir registre ci-dessous et carnet de sources dans l’expérience).

### 0:35–1:00 · La vision (25 s)

**Message principal :** Symbiose relie observations, connaissances et projets d’aménagement.

**Statut :** Fonction documentée.

**Texte oral proposé :** Notre solution, Symbiose, associe reconnaissance animale, validation humaine et données du territoire. Elle s’adresse aux collectivités, aux propriétaires, aux aménageurs et aux naturalistes. Son originalité : partir d’un projet concret et rendre visibles les preuves, les incertitudes et les adaptations à examiner. L’humain garde la décision.

**Écran :** Un territoire. Des liens à comprendre. — Collectivités ; Agriculteurs et propriétaires ; Aménageurs et naturalistes.

**Interaction / animation :** Le survol révèle les liens entre les milieux normands ; le trajet reste illustratif.

**Transition :** Le regard suit la vallée et rejoint le réseau des rivières.

**Sources locales :** manifesto, parcels, design, annex (voir registre ci-dessous et carnet de sources dans l’expérience).

### 1:00–1:35 · Les données (35 s)

**Message principal :** Observations validées, cadastre, occupation agricole et référentiels environnementaux.

**Statut :** Fonction documentée.

**Texte oral proposé :** Le prototype croise les vidéos validées avec le cadastre, les prairies déclarées au RPG 2024, les zonages IGN et les zones humides de la DREAL Normandie. OpenAlex, Crossref et Europe PMC alimentent la recherche documentaire. Chaque source garde sa provenance. Les consultations archivées de Caen et Carentan montrent un fonctionnement technique ; elles ne mesurent aucun effet écologique. Un point consulté ne décrit pas toute une parcelle.

**Écran :** Faire converger les connaissances. — Vidéos et validation humaine ; Cadastre · RPG 2024 · commune ; ZNIEFF · Natura 2000 · zones humides ; Publications scientifiques.

**Interaction / animation :** Quatre affluents documentaires convergent ; une matrice interactive montre les réponses IGN réellement archivées.

**Transition :** Le courant entraîne le regard sous la surface, vers une perspective d’évolution.

**Sources locales :** manifesto, parcels, territory, territory-validation, wetlands, documents (voir registre ci-dessous et carnet de sources dans l’expérience).

### 1:35–1:55 · Les perspectives (20 s)

**Message principal :** Hydrophones, caméras immergées et autres capteurs : des pistes à développer et à valider.

**Statut :** Perspective · non opérationnelle.

**Texte oral proposé :** Aujourd’hui, nous travaillons sur les vidéos terrestres. Demain, des hydrophones ou des caméras immergées pourraient élargir l’observation. Ce sont des perspectives : ces capteurs ne sont pas opérationnels dans le prototype. Chaque nouveau milieu demandera des données et une validation adaptées.

**Écran :** Demain, écouter aussi le vivant. — Hydrophones ; Caméras immergées ; Nouveaux protocoles à valider.

**Interaction / animation :** Des ondes illustratives évoquent l’écoute ; aucun signal acoustique réel n’est revendiqué.

**Transition :** La caméra remonte vers les roseaux et la chaîne d’analyse actuelle.

**Sources locales :** manifesto, vision (voir registre ci-dessous et carnet de sources dans l’expérience).

### 1:55–2:30 · Le moteur technique (35 s)

**Message principal :** De la vidéo au dossier : une chaîne traçable, avec des étapes distinctes.

**Statut :** Fonction documentée.

**Texte oral proposé :** Nous extrayons des images de la vidéo. MegaDetector localise les animaux ; un modèle PyTorch propose une espèce, puis le suivi relie les observations dans le temps. La personne vérifie l’espèce et le recadrage. Les données ouvertes et les publications enrichissent ensuite le dossier. Les traitements sont locaux et asynchrones, avec une seule tâche GPU lourde à la fois. Aucun entraînement ne démarre automatiquement.

**Écran :** L’IA propose. L’humain vérifie. — Vidéo ; Extraction ; Reconnaissance et suivi ; Validation humaine ; Open Data et publications ; Pistes d’aménagement.

**Interaction / animation :** Un fil lumineux traverse six étapes dans le paysage ; chaque étape explique son rôle au clic.

**Transition :** Les annotations se rapprochent et deviennent le cadre de la démonstration produit.

**Sources locales :** vision, review, rag, architecture (voir registre ci-dessous et carnet de sources dans l’expérience).

### 2:30–4:00 · La démonstration (90 s)

**Message principal :** 90 secondes dans l’application. Lecture et pause sous votre contrôle.

**Statut :** Fonction documentée.

**Texte oral proposé :** [Démonstration vidéo locale : 90 secondes. Lancer manuellement. Montrer l’import, la validation d’une observation, le projet localisé, ses sources et une alternative conditionnelle. Si la vidéo est absente, annoncer le remplacement par une capture issue du manifeste ; ne pas prétendre avoir démontré le parcours complet.]

**Écran :** Du terrain à un dossier partagé. — Importer les vidéos ; Valider une observation ; Examiner un projet et ses sources.

**Interaction / animation :** Lecteur HTML natif, sans lecture automatique. Capture du manifeste en remplacement et sélection possible d’un fichier vidéo local.

**Transition :** Le cadre de l’interface s’ouvre à nouveau sur le bocage puis le littoral.

**Sources locales :** manifesto, parcels, review, design-validation (voir registre ci-dessous et carnet de sources dans l’expérience).

### 4:00–4:25 · Les impacts (25 s)

**Message principal :** Des bénéfices attendus pour les acteurs normands ; leur ampleur reste à évaluer sur le terrain.

**Statut :** Bénéfice attendu · non mesuré.

**Texte oral proposé :** Le prototype documente douze alternatives pour cinq types d’intervention, dont les clôtures et l’éclairage. Les bénéfices attendus sont un examen facilité des observations et des projets mieux informés. Ces options restent conditionnelles : leur efficacité locale n’est pas mesurée. Il faut vérifier les habitats, les usages et l’applicabilité des sources avec les acteurs du terrain.

**Écran :** Mieux anticiper. Mieux adapter. — Collectivité : examiner un éclairage ; Propriétaire : étudier une clôture ; Aménageur : revoir une implantation.

**Interaction / animation :** Trois usages se déploient devant une évocation discrète d’Étretat ; le nombre d’alternatives est relié à sa source.

**Transition :** La lumière baisse ; les liens du territoire rejoignent la forêt nocturne.

**Sources locales :** manifesto, design, design-validation (voir registre ci-dessous et carnet de sources dans l’expérience).

### 4:25–5:00 · L’équipe et la suite (35 s)

**Message principal :** ARQ · Arden, Romain et Quentin. Passer du prototype à une évaluation de terrain.

**Statut :** Perspective · non opérationnelle.

**Texte oral proposé :** Nous sommes ARQ : Arden, Romain et Quentin. Pour changer d’échelle, nous proposons de rechercher des terrains pilotes en Normandie, un accompagnement naturaliste et des moyens de consolidation technique. Les prochaines étapes : valider les observations, mesurer l’utilité pour les utilisateurs et évaluer les ressources consommées. Aucun partenariat n’est annoncé. Pour mieux protéger le vivant, commençons par mieux le comprendre.

**Écran :** Pour mieux protéger le vivant, commençons par mieux le comprendre. — Terrains pilotes à rechercher ; Expertise naturaliste à mobiliser ; Robustesse et sobriété à évaluer.

**Interaction / animation :** Le logo apparaît avec un lien configurable vers la connexion ou l’inscription.

**Transition :** Arrêt final. L’utilisateur choisit d’entrer dans l’application.

**Sources locales :** manifesto, architecture, design-validation (voir registre ci-dessous et carnet de sources dans l’expérience).

## Correspondance avec les attendus du jury

| Attendu de la demande | Scènes | Couverture |
|---|---|---|
| Problème | Forêt | Données dispersées et difficulté à préparer une décision locale. |
| Solution | Ciel · Zone humide · Démonstration | Chaîne vidéo, contrôle humain et dossier contextualisé. |
| Impacts | Littoral | Bénéfices attendus séparés des mesures techniques ; pas de gain écologique chiffré. |
| Équipe | Forêt nocturne | ARQ : Arden, Romain et Quentin ; rôles individuels non documentés. |
| Besoins pour changer d’échelle | Forêt nocturne | Proposition : pilotes, expertise et consolidation ; aucun partenaire ni financement acquis. |
| Originalité | Ciel · Démonstration | Partir des interventions du projet et rendre les preuves consultables. |
| Innovation | Zone humide | Vision, validation humaine et recherche documentaire reliées aux interventions. |
| Données ouvertes | Rivières | Producteurs, usages, millésime RPG et limites des consultations ponctuelles. |
| Faisabilité | Zone humide · Démonstration | Socle local existant, recettes techniques archivées et lecteur local. |
| Numérique responsable | Zone humide · Forêt nocturne | Traitements locaux, GPU sérialisé ; consommation et utilité à mesurer. |
| Pertinence territoriale | Rivières · Littoral | Sources DREAL Normandie et archives de points normands ; usages proposés aux acteurs locaux. |
| Qualité de la présentation orale | Ensemble du parcours | Script de 5 minutes, 90 secondes réservées à la vidéo, mots simples et arrêts manuels ; répétition à effectuer. |

## Registre de sources

| Identifiant | Document |
|---|---|
| annex | annexe_règlement_datathon_2026 (1).pdf, § 3 (thématique), § 4 (livrables), § 5 (six critères) ; transcription locale embarquée |
| description | Descriptif_projet_Datathon (1).docx : trame vierge à sept rubriques ; aucun résultat supplémentaire |
| jury-questions | image (4).png : problème, solution, impacts, équipe, besoins pour changer d’échelle |
| manifesto | Manifeste - Symbiose - Equipe ARQ.pdf, p. 1–3 (discours) et 3–13 (application) ; transcription locale embarquée et capture p. 7 |
| architecture | [README](../README.md), socle local et exploitation |
| parcels | [Parcelles et données utilisées](PARCEL_DOSSIERS.md) |
| territory | [Contexte territorial](TERRITORIAL_CONTEXT.md) |
| territory-validation | [Recette et archives IGN](TERRITORIAL_VALIDATION.md) |
| wetlands | [DREAL Normandie](DREAL_WETLANDS.md) |
| design | [Alternatives de conception](PROJECT_DESIGN.md) |
| design-validation | [Recette des alternatives](PROJECT_DESIGN_VALIDATION.md) |
| vision | [Pipeline vision](../workers/vision/INFERENCE.md) |
| review | [Validation humaine](../HUMAN_REVIEW.md) |
| documents | [Worker scientifique](../workers/documents/README.md) |
| rag | [Recherche et génération documentaires](RAG.md) |

## Deux modes de lecture

- Exploration : scroll libre, huit chapitres, carnet de sources et détails techniques.
- Présentation : flèches gauche/droite ou Page précédente/suivante, Début/Fin, Espace pour lire/pause ; arrêt automatique au prochain chapitre. Les contrôles, dialogues et le lecteur conservent leurs touches natives.
- Le raccourci Démonstration rejoint 2:30. La vidéo se lance seulement par geste utilisateur, se met en pause en quittant la scène, à l’ouverture du carnet et lorsque l’onglet est masqué.
- Le compteur indique la position dans le script de cinq minutes, pas le temps réel de parole ni le temps joué par le média. La démonstration est manuelle et ne déclenche aucune reprise automatique du récit.
- Plein écran sur action explicite, avec message si l’API est indisponible ; les mouvements réduits gardent la navigation et désactivent la lecture animée.

## Lancer et configurer

```powershell
cd frontend
npm.cmd run dev
# Build typé et tests sans GPU IA
npm.cmd run build
npm.cmd test
npm.cmd run test:e2e -- pitch.spec.ts narrative.spec.ts
# Régénérer ce document et la matrice d’archives après modification des sources
node scripts/export-pitch.mjs
```

Avec le socle habituel : `docker compose up -d --build --no-deps frontend`. Ouvrir `http://localhost:8080/` hors session ; une session active conserve l’accueil métier existant. Tous les médias, textes, géométries et archives de cette expérience sont servis localement. Les liens vers les producteurs restent facultatifs et nécessitent Internet ; le backend et les services publics restent nécessaires pour analyser de nouvelles données dans l’application.

Déposer la vraie vidéo dans `frontend/public/experience-media/demo.mp4` ou `demo.webm` puis reconstruire. On peut aussi choisir un fichier local depuis la scène, sans téléversement. Configuration au build Vite : `VITE_SYMBIOSE_APP_URL` (défaut `/connexion`), `VITE_SYMBIOSE_DEMO_URL` (chemin local absolu optionnel), `VITE_SYMBIOSE_DEMO_CAPTIONS_URL` (WebVTT français local optionnel). Avec Docker, passer ces variables depuis `frontend/.env.local` (fichier ignoré copié au build) ; les variables de conteneur à l’exécution ne reconfigurent pas les fichiers statiques. Une configuration média distante est refusée. Un fichier absent ou illisible affiche un état explicite. Fournir les sous-titres et une vidéo de 90 s pour la recette finale ; le lecteur avertit si la durée s’en écarte de plus de 5 s.
