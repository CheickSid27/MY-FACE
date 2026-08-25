# Deploiement

Ce guide couvre le deploiement self-hosted utilise en pratique pour ce projet : Docker Compose sur
une machine avec GPU (acceleration InsightFace), Postgres gere (Neon) et stockage objet gere
(Cloudflare R2), exposes publiquement via Cloudflare Tunnel. Adaptez selon votre infrastructure.

## 1. Base de donnees : Neon (Postgres serverless, gratuit)

1. Creez un projet sur [neon.tech](https://neon.tech), activez l'extension `vector` (pgvector) dans
   l'onglet SQL Editor : `CREATE EXTENSION IF NOT EXISTS vector;`
2. Recuperez la chaine de connexion **directe** (pas l'endpoint `-pooler`) :

   ```
   DATABASE_URL=postgresql+asyncpg://<user>:<password>@<endpoint>.neon.tech/<db>?ssl=require
   ```

   ⚠️ **Piege connu** : l'endpoint `-pooler` de Neon (PgBouncer en mode transaction) est
   incompatible avec les requetes preparees cote serveur qu'asyncpg utilise par defaut — erreur
   `InvalidSchemaNameError: no schema has been selected to create in` sur des requetes pourtant
   valides. Le backend garde de toute facon son propre pool de connexions SQLAlchemy : le pooler de
   Neon n'apporte rien ici.
3. `?ssl=require` (pas `sslmode=`, une convention `psycopg` non comprise par le driver `asyncpg`).

## 2. Stockage objet : Cloudflare R2 (S3-compatible, gratuit jusqu'a 10 Go)

1. Creez un bucket R2 dans le dashboard Cloudflare, puis un jeton API R2 (Account API Token, avec
   permissions lecture/ecriture sur le bucket).
2. Renseignez dans `.env` :

   ```
   S3_ENDPOINT_URL=https://<account_id>.r2.cloudflarestorage.com
   S3_ACCESS_KEY=<access_key>
   S3_SECRET_KEY=<secret_key>
   S3_BUCKET=<nom_du_bucket>
   S3_REGION=auto
   S3_PUBLIC_URL=https://<account_id>.r2.cloudflarestorage.com
   ```

   R2 est deja public en HTTPS des sa creation : pas besoin d'un tunnel/second endpoint (contrairement
   a MinIO en local).

## 3. Exposition publique : Cloudflare Tunnel (quick tunnel)

Le service `tunnel-app` du `docker-compose.yml` lance un tunnel Cloudflare **sans compte requis**,
qui expose nginx (donc frontend + backend) sur une URL publique `https://xxxx.trycloudflare.com`.

```bash
docker compose up -d tunnel-app
docker logs -f myface-tunnel-app-1   # cherchez "Your quick Tunnel has been created"
```

⚠️ **URL ephemere** : elle change a chaque redemarrage du conteneur `tunnel-app`. Apres chaque
changement, mettez a jour dans `.env` :

```
APP_BASE_URL=https://<nouvelle-url>.trycloudflare.com
NEXT_PUBLIC_API_URL=https://<nouvelle-url>.trycloudflare.com/api
```

puis recreez `backend` et `frontend` (les variables `NEXT_PUBLIC_*` sont figees au demarrage du
process Next.js) :

```bash
docker compose up -d backend frontend
docker restart myface-nginx-1   # voir gotcha ci-dessous
```

**Pour une URL stable** (recommande en production reelle) : achetez un nom de domaine, ajoutez-le a
un compte Cloudflare, et remplacez le quick tunnel par un [tunnel nomme](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/create-remote-tunnel/).

## 4. Piege operationnel : cache DNS nginx

nginx resout le nom d'hote de ses upstreams (`backend`, `frontend`) **au demarrage** et met en cache
cette resolution. Recreer le conteneur `backend` ou `frontend` (nouvelle IP interne Docker) sans
redemarrer `nginx` provoque des erreurs 502. **Reflexe systematique** apres toute recreation de
`backend`/`frontend` :

```bash
docker restart myface-nginx-1
```

## 5. Notifications push (VAPID)

Generez une paire de cles VAPID unique pour votre deploiement (ne jamais la regenerer sans
supprimer aussi les abonnements existants en base — ils deviendraient invalides silencieusement) :

```bash
docker compose exec backend python3 -c "
from py_vapid import Vapid02
from cryptography.hazmat.primitives import serialization
import base64

v = Vapid02()
v.generate_keys()
pub_raw = v.public_key.public_bytes(
    encoding=serialization.Encoding.X962,
    format=serialization.PublicFormat.UncompressedPoint,
)
print('VAPID_PUBLIC_KEY=' + base64.urlsafe_b64encode(pub_raw).decode().rstrip('='))
print('VAPID_PRIVATE_KEY=\"' + v.private_pem().decode().strip() + '\"')
"
```

Renseignez `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY` (backend) et `NEXT_PUBLIC_VAPID_PUBLIC_KEY`
(frontend, meme valeur que la cle publique) dans `.env`, ainsi que `VAPID_SUBJECT` (une adresse
`mailto:` de contact, requise par la spec Web Push). Cote utilisateur : ouvrir la page admin sur
telephone, "Ajouter a l'ecran d'accueil", puis activer les notifications depuis la bannière dediee.

## 6. Dossier surveille

Creez un sous-dossier par evenement sous `./watched-photos/` a la racine du projet (chemin hote,
monte sur `/watched` dans le conteneur backend) :

```
watched-photos/
  <event_id>/     ← photos deposees ici (copie carte SD, logiciel de transfert...)
```

L'ID exact de l'evenement est affiche dans la page admin de l'evenement ("Dossier surveille"). Le
scan tourne toutes les `WATCHED_FOLDER_POLL_SECONDS` (5s par defaut) ; un fichier n'est ingere
qu'apres deux scans consecutifs a taille stable (evite de lire un fichier en cours de copie).

## 7. Migrations base de donnees

```bash
docker compose exec backend alembic upgrade head
```

Appliquee automatiquement au demarrage du conteneur `backend` (voir la commande `CMD` dans
`backend/Dockerfile`) — a executer manuellement uniquement si besoin de reappliquer hors demarrage.

## 8. Sauvegarde / donnees sensibles

- `.env` n'est **jamais** commite (voir `.gitignore`) — il contient toutes les cles secretes
  (base de donnees, stockage, VAPID, SMS).
- `watched-photos/` est local a chaque poste et exclu du depot.
- Les originaux photo restent uniquement dans le stockage objet configure (R2/MinIO/Supabase) :
  pensez a une politique de sauvegarde/versionning cote fournisseur si necessaire.
