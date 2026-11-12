# Accès HTTPS local avec une URL ngrok stable

Le tunnel donne accès à Vue et à son proxy `/api` sur la même origine HTTPS.
L'API, les workers, les modèles et les données restent exécutés et stockés sur le PC.
Le PC, Docker et la connexion Internet doivent rester actifs.

## Configurer le compte

Chaque compte ngrok, même gratuit, possède un domaine de développement fixe,
attribué par ngrok et conservé au redémarrage. Le nom ne peut pas être choisi
avec l'offre gratuite. Un nom personnalisé dépend de l'offre souscrite.
Voir les [domaines ngrok](https://ngrok.com/docs/gateway/domains).

Dans le dashboard ngrok, récupérer le domaine dans
[Domains](https://dashboard.ngrok.com/domains) et l'authtoken dans
[Your Authtoken](https://dashboard.ngrok.com/get-started/your-authtoken).
Ajouter ces valeurs dans le `.env` existant à la racine, sans le remplacer :

```dotenv
NGROK_URL=https://votre-domaine-attribue.ngrok-free.dev
NGROK_AUTHTOKEN=votre_authtoken
```

Utiliser exactement le domaine du compte, avec `https://`, sans chemin ni `/`
final. L'extension peut différer de cet exemple. L'authtoken est un secret ;
`.env` est ignoré par Git. Ne pas publier la sortie de `docker compose config`,
qui contient les variables résolues ; `make ngrok-config` valide sans les afficher.

## Démarrer et arrêter

Initialiser d'abord l'administrateur local selon le
[guide d'authentification](AUTHENTICATION.md). Démarrer la plateforme avec sa
commande habituelle (`make up` pour le socle CPU ou
`make inference-up DEVICE=cuda` pour l'inférence GPU), puis :

```sh
make ngrok-config
make ngrok-up
make ngrok-logs
```

Ouvrir ensuite la valeur de `NGROK_URL`. Le domaine reste identique après un
redémarrage du tunnel tant que ce domaine reste affecté au compte.
`restart: unless-stopped` relance le conteneur avec Docker après un redémarrage
du PC, sauf s'il a été arrêté explicitement.

Sous PowerShell, sans GNU Make :

```powershell
docker compose -f docker-compose.yml -f docker-compose.ngrok.yml config --quiet
docker compose -f docker-compose.yml -f docker-compose.ngrok.yml up -d --no-deps --wait backend frontend
docker compose -f docker-compose.yml -f docker-compose.ngrok.yml up -d --no-deps ngrok
docker compose -f docker-compose.yml -f docker-compose.ngrok.yml logs -f --tail=100 ngrok
```

Ces commandes adaptent uniquement le backend et le frontend existants, puis
démarrent le tunnel. Les workers en cours gardent leur configuration CPU/GPU.
Lors d'un futur redéploiement du backend, conserver le fichier
`-f docker-compose.ngrok.yml` en dernier dans la commande Compose, ou relancer
`make ngrok-up` pour réappliquer les réglages HTTPS.

Pour fermer l'accès public, sans arrêter l'application :

```sh
make ngrok-down
```

Équivalent PowerShell :
`docker compose -f docker-compose.yml -f docker-compose.ngrok.yml stop ngrok`.
Les variables ngrok doivent rester renseignées pour ces commandes Compose.

## Authentification et vérification

Le fichier Compose de base ajoute automatiquement `NGROK_URL` aux origines
autorisées lorsqu'elle est renseignée, même après un redémarrage sans le fichier
optionnel. Celui-ci impose `AUTH_COOKIE_SECURE=true` au backend.
Les sessions et jetons CSRF de l'application
restent obligatoires. Aucun port d'inspection ngrok n'est publié, et l'inspection
des requêtes par l'agent est désactivée.

Les cookies sécurisés sont destinés à HTTPS. Pour revenir au mode HTTP local
après `make ngrok-down`, réappliquer la configuration de base :

```sh
docker compose up -d --no-deps --wait backend
```

Cette commande reprend `AUTH_COOKIE_SECURE` de `.env` (défaut : `false`).
Se reconnecter si nécessaire lorsque l'origine change.

Vérifier dans le navigateur : `/api/health`, connexion/déconnexion, accès direct
à une route Vue comme `/documents`, puis une écriture avec la session active.
Une erreur 403 d'origine peut indiquer une URL différente de `NGROK_URL` ou un
backend redémarré sans le fichier optionnel. Un échec de tunnel est détaillé par
`make ngrok-logs` : vérifier le token, le domaine et les limites du compte.

L'offre gratuite est soumise à des quotas et peut afficher une page
d'avertissement avant le site ; voir les
[limites ngrok](https://ngrok.com/docs/pricing-limits/free-plan-limits).
Les vidéos transitent par ngrok et consomment ces quotas. Ce mode partage
l'application avec son inscription libre existante ; il ne réserve pas l'accès
à une liste d'invités. Il ne remplace pas un hébergement autonome sur VPS.
