# Symbiose — Le voyage du vivant

## Intention

Faire sentir ce qui relie un passage animal, un milieu et une décision humaine. L’image conduit de la proximité du sous-bois à la lecture du territoire, puis revient à une présence discrète dans la forêt. La technologie apparaît comme un instrument d’attention : elle ne transforme pas le paysage en tableau de scores.

La signature du manifeste est « L’humain en symbiose avec la nature » (page 1). Le parcours visuel doit permettre de comprendre le passage observation → proposition de l’IA → validation humaine → connaissance et contexte territorial → réflexion sur les aménagements. Les recommandations ne sont pas des décisions automatiques. Les limites de validation du manifeste, page 2, restent valables dans la narration.

Cette livraison est une **revue de direction artistique**. Les compositions générées et les calques détourés sont réels et consultables ; ils ne constituent pas encore huit environnements animables. Les fonds reconstruits, profondeurs, géométries, passes et vidéos absents sont inventoriés explicitement. Aucun raccord supplémentaire n’est développé ni activé.

## Références et arbitrages

| Priorité | Source du dépôt | Ce qu’elle fixe |
| --- | --- | --- |
| 1 | `Manifeste - Symbiose - Equipe ARQ.pdf`, pages 1–3 | Intention, destinataires, traçabilité, validation humaine et limites des recommandations |
| 1 | Captures du manifeste, pages 3–12, notamment 5 et 7 | Identité opérationnelle : logo blanc existant, verts profonds, verre sombre, accents citron, interfaces calmes |
| 2 | `Symbiose _ Voyage immersif du vivant normand.png` | Ordre des huit atmosphères, récit de cinq minutes, lumière, relation paysage/capteur, place de la démo de 90 secondes |
| 3 | `frontend/src/assets/symbiose-logo.png` et `src/styles/symbiose.css` | Logo exact du produit et palette existante ; aucune marque redessinée |
| 4 | Storyboard fourni et [storyboard de production](STORYBOARD.md) | Découpage des plans, trajectoires, entrées/sorties et besoins de raccord |

La planche possède une variante de symbole végétal. L’instruction explicite de réutiliser le logo du produit prévaut : nous employons **le fichier blanc existant**, sans nouvelle feuille dessinée, recoloration, modification de proportions ou remplacement typographique. Son fond transparent et ses marges d’origine sont conservés. La landing importe ce fichier ; la galerie utilise une copie identique contrôlée par empreinte.

Les captures du manifeste sont les références prioritaires. Des pages ont été rasterisées pour consultation dans `output/symbiose/art-direction/references/`, sans altérer le PDF. Les anciennes captures de démonstration du dépôt peuvent aider à lire les formes et les couleurs, mais leurs chiffres et jauges ne doivent jamais devenir des preuves d’efficacité.

## Grammaire visuelle

| Usage | Valeur | Règle |
| --- | --- | --- |
| Forêt profonde | `#073322` | Valeur d’ancrage du produit ; ombres et surfaces |
| Végétal | `#5b8539` | Feuillage et valeurs médianes, jamais appliqué en teinte uniforme au ciel ou à la craie |
| Accent citron | `#b9ef84` | Navigation, état actif et repère éditorial discret |
| Accent renforcé | `#a8f251` | Focus ou action ponctuelle ; pas de halo dans la nature |
| Ivoire | `#f5f8ef` | Texte et lumière naturelle non brûlée |
| Verre | `rgba(7, 51, 34, .78)` | Panneau lisible, bord fin, reflet très léger, flou d’arrière-plan mesuré |

Ces valeurs viennent des fondations du produit. Chaque milieu dispose de sa propre palette dans le manifest ; les couleurs ne sont pas une LUT appliquée mécaniquement. Les verts restent variés et plausibles. L’eau marine prend un gris vert ; la craie reste ivoire ; la nuit est désaturée sans se transformer en éclairage bleu électrique.

La typographie d’interface reprend Inter si elle est disponible localement, puis Segoe UI/Arial. Aucun chargement de police distante. Une sérif éditoriale sobre peut porter le récit ; elle ne remplace jamais les caractères du logo. Le texte, les repères de parcours et les légendes restent du HTML : aucune donnée, interface ou marque n’est inscrite dans les images générées.

## Un même film

- **Saison et matière** : fin de printemps, feuillus déployés, herbes humides après la pluie, mousses et craie imparfaites. Pas de mélange automne/hiver/tropiques dans les scènes diurnes.
- **Lumière** : lumière matinale douce venant du haut gauche. Elle reste du même côté lors des raccords de regard. La nuit constitue une ellipse temporelle assumée, avec une ouverture lunaire du même côté.
- **Contraste** : proximité détaillée, valeurs médianes riches, arrière-plan progressivement moins contrasté. Les rayons existent dans une brume suffisamment présente, pas dans un air arbitrairement lumineux.
- **Optique** : focales équivalentes plein format de 24 à 50 mm, perspective contenue. La profondeur de champ laisse lire le milieu. Aucun grand-angle extrême ou bokeh qui transforme les espèces en accessoires.
- **Cadre** : les bords proches donnent l’échelle ; le couloir de déplacement reste lisible. Les compositions protègent un cadrage 16:9 et ménagent une zone calme pour la parole, sans imposer un panneau sur tous les plans.
- **Mouvement futur** : lent et motivé par une découverte. Une translation d’image ou un fondu ne sera jamais décrit comme une traversée réelle d’un milieu.
- **Présence humaine** : capteurs modestes, mats, montés de façon plausible. Aucun laboratoire futuriste, drone décoratif ou écran fluorescent.

La cohérence a été examinée sur les huit compositions produites : direction de lumière, familles de verts et de matières, eau tempérée, silhouettes et retour aux feuillus. Cela constitue une sélection artistique de travail, **pas une validation de l’utilisateur ni une certification écologique**. Les écarts de cadrage et les silhouettes d’Étretat doivent encore être confrontés à des références géographiques pour une reconstitution métrique.

## Ancrage et honnêteté des représentations

La Normandie est suggérée par les feuillus tempérés, les réseaux de haies, le relief bocager, les ripisylves basses, les roseaux, l’eau de la Manche et la craie de la côte d’Albâtre. Éviter les montagnes, les mangroves, le récif tropical, les prairies sans limites à l’américaine et la forêt de conifères du nord-ouest américain.

Pour le littoral, **Porte d’Aval et Aiguille doivent être séparées, entièrement visibles et reconnaissables ensemble** : falaise crayeuse stratifiée, ouverture traversante de l’arche, aiguille distincte et eau entre les masses. Le plan produit montre ces deux repères. Il reste une évocation générée ; sa géométrie n’est pas une reconstruction exacte. Aucun soleil de carte postale, lettrage touristique, mouette géante ou foule ajoutée pour signifier le lieu.

La référence géographique consultée est [la présentation des falaises par l’office Le Havre Étretat Normandie Tourisme](https://www.lehavre-etretat-tourisme.com/decouvrir/les-incontournables/decouvrir-etretat/les-falaises-detretat/). Aucune de ses photographies n’a été téléchargée, copiée ou distribuée dans les assets.

Chaque scène affiche « Image générée par IA » ou « Évocation générée d’Étretat ». Les images ne sont jamais qualifiées de prises de vue documentaires. Les animaux sont des sujets illustratifs : ni observation validée, ni preuve de présence, ni résultat du classificateur. Le héron, les poissons et les capteurs acoustiques ne sont pas présentés comme des fonctions déjà prises en charge par le modèle terrestre à dix espèces.

Les anciens fonds du produit sont laissés intacts. En particulier, les images historiques de Californie, de Suisse et du mont Rainier ne sont pas réétiquetées « Normandie ». Le manifest conserve cette exclusion et renvoie au fichier historique `frontend/src/assets/backgrounds/SOURCES.md` pour leur provenance.

## Profondeur : contrat de production

Le plan principal est une composition d’intention. Le premier plan est un PNG avec alpha, dérivé de cette composition, candidat au compositing. **Il ne faut pas déplacer ce calque au-dessus du master complet** : le feuillage y est déjà incrusté et apparaîtrait en double. Il faut d’abord reconstruire le fond masqué, contrôler l’overscan et aligner les silhouettes.

Les calques issus de génération restent des candidats : la transparence est mesurée, mais le détourage n’est pas garanti identique au pixel près. Les feuilles, reflets et franges claires doivent être contrôlés sur fond ivoire et vert sombre, sans confondre un liseré clair parasite avec un rayon de soleil. La géométrie, les profondeurs et l’animation exigent une revue distincte.

Pour la montée dans la canopée, le franchissement de l’eau et le déplacement autour d’Étretat, préparer des géométries ou des plans pré-rendus avec repères fixes. Un unique master, même accompagné d’une profondeur monoculaire, ne révèle pas les surfaces cachées. Les prompts des ressources manquantes décrivent les vues et passes à produire ; ils ne prétendent pas que ces fichiers existent.

Objectifs de production ultérieure : masters 3840 × 2160, fonds avec 15 % d’overscan, alpha propre, profondeurs 16 bits, GLB légers, textures KTX2 après validation. Clips complexes à 1920 × 1080, 25 images/s, sans texte incrusté ; prévoir affiches et fallback fixe. **Les dimensions réellement obtenues aujourd’hui sont celles des manifests**, pas ces objectifs futurs. Aucun agrandissement artificiel n’est présenté comme du détail natif 4K.

Le budget d’exploitation sera contrôlé lors de l’intégration : une scène active et sa voisine, résolution adaptée, chargement progressif, pas de décodage des huit masters et de tous les alphas en permanence. La présente galerie est un outil de revue séparé et ne charge pas les images sur les autres pages du produit.

## État de livraison et critère de passage

Les huit plans principaux et huit premiers plans font l’objet d’un inventaire vérifié. Fonds reconstruits, profondeurs, brumes séparées, géométries et clips restent absents, ainsi que la démonstration produit de 90 secondes. Le générateur disponible est un outil d’images ; aucune vidéo n’a été générée.

Le prochain jalon est une validation **des huit compositions comme un film**, puis des couches et des points d’entrée/sortie. Le manifest conserve `transitionWorkAllowed: false`, `mainPlatesApproved: false` et `layeredScenesReady: false`. Une simple présence de fichier ne peut lever ces états. Les six chapitres encore prévus dans le moteur restent inactifs ; le prototype forêt → ciel conserve son rôle de maquette technique.

Consulter [le pipeline et les ressources absentes](PIPELINE.md), [le storyboard](STORYBOARD.md) et [le manifest JSON](../../frontend/public/experience-art/manifest.json).
