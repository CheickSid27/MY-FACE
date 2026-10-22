# Deploiement

Mise a jour : 22 octobre 2026.

Ce guide couvre le deploiement self-hosted utilise en pratique pour ce projet : Docker Compose sur
une machine avec GPU (acceleration InsightFace), Postgres gere (Neon) et stockage objet gere
(Cloudflare R2), exposes publiquement via un tunnel Cloudflare nomme sur `app.myfaceci.online`.
Adaptez selon votre infrastructure. Le choix d'un vrai serveur (CPU + GPU a la demande, ou serveur
GPU) est en reflexion : tant que tout tourne sur le PC, **MYFACE est coupe quand le PC ou Docker
Desktop est arrete**.

## 1. Base de donnees : Neon (Postgres serverless, gratuit)

1. Creez un projet sur [neon.tech](https://neon.tech), activez l'extension `vector` (pgvector) dans
   l'onglet SQL Editor : `CREATE EXTENSION IF NOT EXISTS vector;`
2. Recuperez la chaine de connexion **directe** (pas l'endpoint `-pooler`) :

   ```
   DATABASE_URL=postgresql+asyncpg://<user>:<password>@<endpoint>.neon.tech/<db>?ssl=require
   ```

   ⚠️ **Piege connu** : l'endpoint `-pooler` de Neon (PgBouncer en mode transaction) est
   incompatible avec les requetes preparees cote serveur qu'asyncpg utilise par defaut, erreur
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

## 3. Exposition publique : tunnel Cloudflare nomme

Le domaine `myfaceci.online` est chez Cloudflare. Le service `tunnel-domaine` du
`docker-compose.yml` (profil `domaine`) lance `cloudflared` avec le jeton du tunnel
(`CLOUDFLARE_TUNNEL_TOKEN` dans `.env`) et expose nginx sur `https://app.myfaceci.online`, sans
port ouvert sur le PC. Le site vitrine `myfaceci.online` est servi a part par un Worker Cloudflare
deploye depuis la branche `main` (dossier `site-vitrine/`).

```bash
docker compose --profile domaine up -d tunnel-domaine
```

L'ancien quick tunnel (`trycloudflare.com`, adresse changeante) n'est plus utilise.

**Adresse de l'API cote navigateur** : gardez `NEXT_PUBLIC_API_URL=/api` (relatif). nginx sert
le site et l'API sur la meme adresse, donc le frontend fonctionne a l'identique en local
(`http://localhost`) et en ligne, sans recompilation.

`APP_BASE_URL=https://app.myfaceci.online` alimente tous les liens envoyes ou imprimes : e-mails,
QR code de telechargement, lien invite court (`/e/CODE`), QR et affiche A4 de l'evenement, retour
de Paystack. Tant qu'il vaut `localhost`, la page de l'evenement affiche un avertissement. Le
backend ne relit `.env` qu'a sa creation : apres une modification,
`docker compose up -d --no-deps backend` puis redemarrer nginx (section 4).

**Limites anti-abus derriere le tunnel** : tout le trafic public arrive a nginx par le conteneur
`cloudflared`. nginx lit donc l'adresse reelle du client dans l'en-tete `CF-Connecting-IP`
(`set_real_ip_from 172.16.0.0/12` + `real_ip_header`, voir `nginx/nginx.conf`) : les limites
(connexion, scan facial, visages, code court) s'appliquent par adresse et non a tout l'evenement a
la fois. Relevees le 22/10 : les invites d'un meme Wi-Fi de salle ou d'un meme operateur 4G
partagent souvent une adresse (90 selfies/min, 240 groupes de visages/min, 60 codes/min).

## 4. Piege operationnel : cache DNS nginx

nginx resout le nom d'hote de ses upstreams (`backend`, `frontend`) **au demarrage** et met en cache
cette resolution. Recreer le conteneur `backend` ou `frontend` (nouvelle IP interne Docker) sans
redemarrer `nginx` provoque des erreurs 502. **Reflexe systematique** apres toute recreation de
`backend`/`frontend` :

```bash
docker restart myface-nginx-1
```

## 5. Notifications push (VAPID)

Generez une paire de cles VAPID unique pour votre deploiement. **La cle privee doit etre en base64url
brute (43 caracteres), pas un PEM** : un PEM sur plusieurs lignes dans `.env` n'est pas lu par la
bibliotheque d'envoi, et aucune notification ne part (constate le 22/10) :

```bash
docker compose exec backend python3 -c "
from py_vapid import Vapid02, b64urlencode
from cryptography.hazmat.primitives import serialization
v = Vapid02()
v.generate_keys()
pub = v.public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
priv = v.private_key.private_numbers().private_value.to_bytes(32, 'big')
print('VAPID_PUBLIC_KEY=' + b64urlencode(pub))
print('VAPID_PRIVATE_KEY=' + b64urlencode(priv))
"
```

Renseignez `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY` (backend) et `NEXT_PUBLIC_VAPID_PUBLIC_KEY`
(frontend, meme valeur que la cle publique, puis reconstruire le frontend), ainsi que
`VAPID_SUBJECT` (`mailto:` de contact). Changer de cles rend les anciens abonnements invalides : ils
sont nettoyes a la premiere erreur 401/403/404/410, et MYFACE Pro se reabonne seul a l'ouverture.
Cote utilisateur : installer MYFACE Pro (« Installer l'application » dans Compte), puis activer les
notifications.

## 5 bis. E-mails (Resend)

Confirmation de l'adresse des photographes et mot de passe oublie, par SMTP : `SMTP_HOST`
(`smtp.resend.com`), `SMTP_PORT` (465), `SMTP_USE_SSL=true`, `SMTP_USERNAME` (`resend`),
`SMTP_PASSWORD` (cle API Resend), expediteur sur le domaine verifie `myfaceci.online`. Des que
l'envoi est configure, la confirmation d'adresse devient obligatoire (`EMAIL_VERIFICATION_REQUIRED`
pour forcer l'un ou l'autre) et les inscriptions non confirmees en
`UNVERIFIED_ACCOUNT_TTL_MINUTES` (5) sont annulees. A faire : enregistrement DMARC dans Cloudflare.

## 5 ter. Paiement en ligne (Paystack)

`PAYSTACK_PUBLIC_KEY` et `PAYSTACK_SECRET_KEY` (cles de test `pk_test_` / `sk_test_` au 22/10).
Dans le tableau de bord Paystack, l'adresse de webhook est
`https://app.myfaceci.online/api/payments/paystack/webhook`. Sans cle, le paiement en ligne
disparait de l'interface (`GET /meta/features`). Avant les vrais paiements : passer aux cles
`live`, confirmer avec Paystack les versements Mobile Money vers les sous-comptes, et faire
accepter aux photographes leurs conditions (frais Paystack a leur charge).

## 5 quater. Conservation des donnees

`RETENTION_ENABLED=true` active la suppression automatique declaree a l'ARTCI (photos et visages
90 jours apres l'evenement, telephone des commandes apres 1 an ; voir ARCHITECTURE.md). Sans cette
variable, le passage quotidien ne fait que simuler.

## 6. Dossier surveille

Les photographes choisissent leur propre dossier dans leur navigateur (Chrome ou Edge sur
ordinateur), rien a installer. Ce qui suit concerne le dossier du PC de la borne, reserve a
l'equipe MYFACE.

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
`backend/Dockerfile`), a executer manuellement uniquement si besoin de reappliquer hors demarrage.

## 7 bis. Redemarrages, mises a jour et logs

- **Backend** : le code est monte en bind-mount, un `docker restart myface-backend-1` suffit pour
  prendre en compte une modification Python (uvicorn tourne sans rechargement automatique) ; une
  nouvelle dependance demande `docker compose build backend`.
- **Frontend** : image de production compilee, toute modification (y compris des `NEXT_PUBLIC_*`)
  demande `docker compose build frontend` puis `docker compose up -d --no-deps frontend`.
- **nginx** : `nginx.conf` est copie dans l'image (`docker compose build nginx`) ; le redemarrer
  apres toute recreation de `backend`/`frontend` (cache DNS, voir section 4).
- **Logs applicatifs** : `docker logs -f myface-backend-1` affiche les messages `myface.*`
  provider GPU utilise, indexation, dossier surveille, rattrapages au demarrage (commandes
  expirees, indexations reprises, filigranes generes, groupes de visages pre-calcules).

## 7 ter. Memoire du PC et redemarrage

- Windows est presque a court de memoire : construire **une image a la fois**
  (`docker compose build backend`, puis `build frontend`), base de test arretee
  (`docker compose stop db`). Ne pas lancer la copie de test des tests d'interface
  (`docker-compose.e2e.yml`) sur ce PC : Docker s'est arrete plusieurs fois (production coupee).
- **Docker Desktop ne redemarre pas toujours seul** (panne de 9 h le 21/10, et apres le redemarrage
  du PC le 22/10 : Cloudflare repondait 530). Activer dans Docker Desktop « Start Docker Desktop
  when you sign in », puis verifier que les conteneurs repartent (`restart: unless-stopped`).
  Relance a la main :

  ```bash
  docker compose up -d --no-deps backend frontend nginx tunnel-domaine
  ```

## 8. Sauvegarde / donnees sensibles

- `.env` n'est **jamais** commite (voir `.gitignore`), il contient toutes les cles secretes
  (base de donnees, stockage, VAPID, SMS, Resend, Paystack, tunnel).
- `watched-photos/` est local a chaque poste et exclu du depot.
- Les originaux photo restent uniquement dans le stockage objet configure (R2/MinIO/Supabase) :
  pensez a une politique de sauvegarde/versionning cote fournisseur si necessaire.
