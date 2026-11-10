# Adapter un projet d’aménagement

L’analyse territoriale présente désormais des **alternatives concrètes de conception** pour chaque intervention déclarée. Le parcours est : **Projet initial → Alternatives à étudier → Justifications → Conditions et limites**. Il fonctionne avec le moteur déterministe existant, sans attendre un LLM ou le complément documentaire.

## Ce que l’utilisateur peut comparer

| Intervention déclarée | Alternatives proposées | Exemples de changements au projet |
|---|---|---|
| Clôture | Modifier le tracé ; limiter le périmètre clôturé ; examiner une conception adaptée aux déplacements de faune | Tracé et accès déplacés, linéaire réduit, type ou segments de clôture à réexaminer |
| Éclairage extérieur | Éviter certains points lumineux ; réduire la durée de fonctionnement ; adapter l’orientation | Points supprimés ou déplacés, programmation réduite, flux ciblé sur les usages |
| Suppression de végétation | Implantation préservant les éléments présents ; emprise de suppression plus limitée | Constructions ou accès déplacés, éléments conservables intégrés au chantier |
| Terrassement | Implantation différente ; emprise de terrassement réduite | Plan de travaux ajusté, circulations ou stockages temporaires resserrés |
| Imperméabilisation | Éviter des surfaces revêtues non indispensables ; examiner des revêtements perméables | Surfaces réduites, structure, drainage et entretien à réexaminer |

Les douze options sont conditionnelles. Les arbres, haies, déplacements de faune, sols infiltrants ou autres caractéristiques du site ne sont jamais supposés présents. Chaque option précise ce qui doit être observé ou étudié avant de pouvoir l’appliquer. Les caractéristiques initiales non renseignées restent à préciser ; aucune géométrie, dimension, économie ou efficacité n’est inventée.

## Trois niveaux de justification

| Niveau API | Libellé | Conditions d’attribution |
|---|---|---|
| `exploratory` | Exploratoire | Intervention déclarée et répertoire de conception ; aucune preuve pertinente de contexte citée pour cette intervention |
| `contextualized` | Contextualisé | Contexte vérifié pertinent et référencé : faune terrestre validée pour la clôture, identification humaine pour l’éclairage, intersection IGN pour végétation/terrassement/imperméabilisation |
| `scientifically_qualified` | Scientifiquement qualifié · sous conditions | Source identifiée comme scientifique, extrait, page positive, empreinte SHA-256, applicabilité examinée et lien explicite avec **cette alternative**, cette catégorie ERC et une espèce humainement confirmée citée |

**Contextualisé ne signifie pas efficace sur le site.** Une intersection motive un examen, sans prouver un habitat ou un impact. Une observation d’animal ne prouve ni sensibilité à l’éclairage, ni déplacement au droit d’une clôture, ni corridor.

Une référence générale de conception ne constitue pas une qualification scientifique locale. Les extraits lexicaux du RAG restent des candidats à examiner ; ils ne changent pas le niveau de justification. Une source revue pour un thème général ou pour une autre alternative ne suffit pas non plus.

Tous les niveaux gardent `status: "conditional_design_option"`, leurs conditions et leurs limites. La compensation reste `not_assessed`. Les anciennes vérifications et propositions écologiques du champ `actions` conservent leurs contrôles de preuve et sont accessibles sous « Vérifications complémentaires et propositions issues des preuves ».

Le parcours automatique ne crée aucune revue d’applicabilité scientifique. Une option peut donc être utile et présentée comme **exploratoire** ou **contextualisée** sans être promue artificiellement. Le niveau scientifique est testé avec des sources synthétiques explicitement qualifiées dans les fixtures, pas avec une prétendue validation écologique de terrain.

## Contrat et persistance

Le résultat JSON ajoute `design_proposals`, une liste facultative pour les analyses historiques. Chaque entrée porte :

- `project_action` : un des cinq codes existants ;
- `initial_intervention` : intervention initialement déclarée ;
- `issue` : enjeu potentiel à examiner ;
- `alternatives[]` : identifiant stable, `category` (`avoid` ou `reduce`), titre, `proposal`, `project_change`, `conditions`, `evidence_refs`, `source_refs`, `justification: {level, reason}`, statut conditionnel et limites.

La version des règles devient `territorial-erc-v2-design`. Aucune table, route ou permission nouvelle n’est nécessaire : l’instantané et l’export JSON existants conservent les propositions, conditions et sources. Les anciennes analyses ne sont pas réécrites. L’interface propose de lancer une nouvelle analyse lorsqu’une version historique n’a pas ces alternatives.

Un changement d’intervention requiert son enregistrement puis une nouvelle analyse, comme auparavant. L’ancienne analyse reste obsolète et consultable avec ses entrées originales. Aucune option d’une intervention retirée n’est conservée dans la nouvelle analyse. La carte, la consultation IGN asynchrone, la protection des comptes et la séparation des modes restent inchangées.

Pour une source scientifique examinée, le champ `design_alternative_ids` désigne les identifiants précis soutenus, par exemple `outdoor_lighting:shorter_operation`. Une chaîne libre ou un simple thème ne remplace pas cette liste. `evidence_type: "scientific"`, `applicability: "reviewed"`, la catégorie, l’intervention, les espèces et les preuves d’extrait sont également contrôlés. Cela étend le contrat interne ; cela n’ajoute pas un formulaire de revue scientifique.

## Démonstration A/B

1. Ouvrir un dossier en **Données réelles**, enregistrer un point et uniquement **Éclairage extérieur**. Lancer l’analyse.
2. Dans « Adapter mon projet », lire les trois options d’éclairage, leurs changements concrets et leurs conditions. Exporter A.
3. Ajouter **Clôture**, enregistrer puis relancer. Les trois options d’éclairage sont conservées ; trois alternatives de clôture apparaissent. Exporter B et consulter leurs références.
4. Retirer l’éclairage, enregistrer puis relancer : seules les alternatives de clôture restent.
5. Répéter avec les trois autres interventions pour comparer des changements d’implantation, d’emprise et de revêtement.

Une observation de faune terrestre humainement validée contextualise l’examen de la clôture ; son absence laisse les options exploratoires. Une réponse IGN vide ou indisponible laisse les options générales accessibles et les incertitudes visibles. Il est normal qu’aucune option ne soit scientifiquement qualifiée lorsque les preuves requises manquent.

## Références générales utilisées

Références consultées le 10 novembre 2026, citées comme **références générales de conception** dans les résultats. Elles ne sont pas présentées comme des études du terrain de l’utilisateur.

- [Ministère — démarche ERC](https://www.ecologie.gouv.fr/politiques-publiques/eviter-reduire-compenser-impacts-lenvironnement) : cadre général des variantes d’évitement et de réduction.
- [Ministère — Trame verte, bleue et noire](https://www.ecologie.gouv.fr/politiques-publiques/trame-verte-bleue) : nécessité de l’éclairage et orientation, comme pistes générales.
- [OFB — Clôtures : impacts sur la faune](https://patbiodiv.ofb.fr/index.php/fiche-methodologique/amenagements-terrestres/clotures-impacts-faune-887) : effets variables selon la conception et les groupes de faune ; prudence sur les données absentes. Le contexte de cette référence concerne notamment le photovoltaïque et n’est pas assimilé au projet de l’utilisateur.
- [Cerema — Désimperméabilisation](https://www.cerema.fr/system/files/documents/2022/11/2022_plaquette_desimpermeabilisation.pdf) : distinction entre revêtement et capacité d’infiltration, nécessité d’examiner le sol et les contraintes.

Voir [la recette des alternatives](PROJECT_DESIGN_VALIDATION.md) et [le contrat territorial conservé](TERRITORIAL_CONTEXT.md).
