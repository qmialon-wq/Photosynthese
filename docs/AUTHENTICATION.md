# Authentification et données personnelles

## Démarrage

```sh
docker compose build backend frontend
docker compose run --rm --no-deps migrate
docker compose up -d --no-deps backend frontend
```

Au premier démarrage, l’API écrit un jeton aléatoire dans
`data/results/auth/bootstrap-token` (ou le répertoire `results/auth` du `DATA_ROOT`
personnalisé). Lire ce fichier localement, ouvrir
<http://localhost:8080/initialisation>, puis choisir le nom, l’adresse e-mail et le
mot de passe du premier administrateur. Le jeton est consommé une seule fois et
le fichier est retiré. Aucun compte ni mot de passe prédéfini n’est créé.

Les données antérieures restent visibles par les administrateurs ; un nouveau
client ne peut pas les récupérer en réutilisant un ancien `X-Reviewer`.

## Rôles et espaces

| Fonction | Client connecté | Administrateur |
| --- | --- | --- |
| Inscription libre | Compte client uniquement | Création de clients et administrateurs |
| Import depuis le navigateur, analyses | Ses vidéos et ses tâches | Toutes les vidéos et tâches |
| Formulaires et dossiers de parcelle | Ses dossiers | Tous les dossiers |
| Validation humaine | Observations des vidéos qu’il a importées | Ensemble des observations |
| Bibliothèque scientifique commune | Consultation et téléchargement | Collecte, import, traduction, retrait |
| Import par chemin local, entraînements et modèles | Non | Oui |
| Gestion des utilisateurs et des demandes d’effacement | Non | Oui |
| Profil, changement de mot de passe, export, suppression | Son compte | Son compte |

Les vidéos sont identifiées par leur contenu dans la bibliothèque de validation :
deux imports du même fichier physique partagent les observations de ce contenu.
Les tâches d’analyse et les dossiers de parcelle restent attribués à leur auteur.
Les permissions sont appliquées avant la pagination et lors de l’accès direct
aux fichiers, tâches, rapports et identifiants fournis à la génération.

`/admin/utilisateurs` permet de rechercher les comptes (200 résultats maximum),
créer un compte, changer un rôle, supprimer un compte et produire un lien de
réinitialisation. Le dernier administrateur actif ne peut être ni supprimé ni
rétrogradé. Un changement de rôle révoque les sessions du titulaire.

Le lien de réinitialisation est confidentiel, valable 30 minutes et utilisable
une seule fois. L’administrateur le transmet lui-même au titulaire par un canal
approprié ; aucun e-mail n’est envoyé automatiquement. Le secret est placé dans
le fragment du lien, puis retiré de la barre d’adresse par l’interface. Cette
version ne vérifie pas la possession des adresses e-mail.

## Sessions et déploiement

Les mots de passe de 12 à 1024 caractères sont hachés avec scrypt et un sel
aléatoire (N=131072, r=8, p=1). Deux calculs simultanés au maximum évitent une
consommation mémoire incontrôlée. Les connexions, inscriptions, réinitialisations
et vérifications sensibles du mot de passe sont limitées via Redis. Le compteur
utilise l’adresse du pair réseau, sans faire confiance aux en-têtes de transfert
fournis par un client ; derrière le proxy, ce plafond peut donc être partagé.

Les sessions opaques sont conservées sous forme de hachage en base. Le cookie
est HttpOnly et SameSite=Lax ; sa durée maximale est de 12 heures, avec expiration
après 2 heures d’inactivité. Aucun jeton de session n’est stocké dans localStorage.
Le jeton CSRF reste en mémoire et est exigé pour les requêtes authentifiées qui
modifient l’état. Les origines des requêtes de modification sont contrôlées.
Les réponses API ne doivent pas être mises en cache.

Compose utilise `AUTH_COOKIE_SECURE=false` pour HTTP sur cette machine, avec
les ports liés à `127.0.0.1`. Avant une exposition distante, mettre en place HTTPS,
définir `AUTH_COOKIE_SECURE=true` et renseigner précisément `AUTH_ALLOWED_ORIGINS`
(schéma, domaine, port). Adapter cette liste si les ports locaux changent. Les
identifiants PostgreSQL d’exemple sont réservés à l’environnement local.

## Suppression et droit à l’effacement

Depuis `/profil`, le titulaire peut modifier son nom ou son adresse e-mail,
changer son mot de passe, télécharger un export JSON et demander la suppression
de son compte en saisissant son mot de passe et `SUPPRIMER`. Le changement d’adresse
exige aussi le mot de passe ; les autres sessions sont alors révoquées. Un
changement ou une réinitialisation du mot de passe révoque toutes les sessions.

La suppression est transactionnelle : date de suppression, retrait de l’adresse
e-mail et du hachage du mot de passe, nom remplacé par « Compte supprimé »,
révocation des sessions et des liens de réinitialisation. Les tâches vidéo en
attente ou en cours reçoivent une demande d’annulation ; les tâches documentaires
en attente sont arrêtées. Une tâche déjà en cours peut terminer, mais son ancien
titulaire ne peut plus accéder au compte. La réinscription crée un nouvel identifiant
et ne récupère pas les données de l’ancien compte.

Une demande d’effacement avec une référence est créée pour les données associées.
L’administration suit ces demandes dans `/admin/utilisateurs`, avec les statuts
à traiter, en cours et clôturée, et une note justifiant les opérations effectuées.
La clôture enregistre le suivi ; elle n’exécute pas de purge automatique.

**Limite explicite : les fichiers, dossiers, historiques et sauvegardes ne sont
pas effacés automatiquement.** Ils peuvent contenir des informations personnelles
dans les formulaires, noms de fichiers ou textes libres. Le responsable du traitement
doit traiter la demande, retirer ces informations dans les stockages concernés,
prendre en compte les copies partagées et les sauvegardes, et documenter les
éventuelles obligations légales de conservation. Les identifiants d’audit conservés
sont pseudonymes et ne doivent pas être considérés comme anonymes. Ne pas inscrire
de mot de passe, de jeton ou de nouvelles données personnelles dans les notes.

La fermeture technique d’un compte ne suffit pas à établir à elle seule la
conformité RGPD : finalités, base légale, information des utilisateurs, durées de
conservation, procédures d’effacement et sécurité du déploiement relèvent aussi
de l’exploitant. Voir le [droit à l’effacement selon la CNIL](https://www.cnil.fr/fr/comprendre-mes-droits/le-droit-leffacement-supprimer-vos-donnees-en-ligne).

L’export JSON comprend le profil, les vidéos, tâches vidéo et documentaires,
dossiers, formulaires, recherches RAG, imports et révisions de validation
attribués au compte. Il n’inclut aucun hachage de mot de
passe ni secret de session. Les fichiers vidéo se téléchargent séparément depuis
la vidéothèque.

## Vérification

```sh
docker compose --profile test run --rm tests pytest tests/documents/test_authentication.py -m integration
cd frontend
npm test
npx playwright test authentication.spec.ts
npm run build
```

Les tests d’authentification utilisent une base isolée et le vrai contrôle d’accès.
Les tests existants des fonctions métier utilisent un administrateur de test
explicitement injecté ; aucun contournement n’existe dans le code de production.
Les diagnostics navigateur sur les services réels demandent un compte de test
fourni avec `BIOSENTINELLE_E2E_EMAIL` et `BIOSENTINELLE_E2E_PASSWORD` (administrateur
pour le diagnostic documentaire), en plus de leurs indicateurs d’activation.
