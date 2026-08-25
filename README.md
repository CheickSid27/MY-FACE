# MYFACE

Plateforme de photos d'evenement avec reconnaissance faciale : les photos prises pendant un
mariage, une remise de diplomes ou tout autre evenement sont indexees automatiquement, et chaque
invite retrouve ses propres photos en scannant son visage (selfie), les achete et les telecharge
en qualite originale — sans jamais avoir a faire defiler des centaines de photos a la main.

Voir [docs/MYFACE_cahier_des_charges_v2.1.md](docs/MYFACE_cahier_des_charges_v2.1.md) pour la
vision produit complete, et [docs/](docs/) pour la documentation technique detaillee.

## Sommaire

- [Fonctionnalites](#fonctionnalites)
- [Stack technique](#stack-technique)
- [Architecture](#architecture)
- [Demarrage rapide](#demarrage-rapide)
- [Variables d'environnement](#variables-denvironnement)
- [Structure du projet](#structure-du-projet)
- [Tests](#tests)
- [Documentation complementaire](#documentation-complementaire)
- [Limites connues](#limites-connues--non-branche)

## Fonctionnalites

**Cote invite** (application borne/mobile, sans compte requis)
- Accueil evenement par lien/QR code unique, galerie complete virtualisee (react-window) pour tenir
  sur des milliers de photos sans ralentir
- **Scan facial** : selfie pris depuis la camera du navigateur (aperçu en mode miroir, effets visuels
  "scanner"), comparaison contre tous les visages indexes de l'evenement (InsightFace + pgvector),
  resultats en quelques secondes
- Vue "personnes detectees" : parcourir des groupes de visages similaires (pre-groupage DBSCAN) sans
  avoir a scanner son visage
- Panier avec mise a jour optimiste (aucune latence percue), animation "vol vers le panier"
- Chargement progressif des photos : miniature instantanee (cache navigateur), puis version nette
  chargee silencieusement en arriere-plan (fondu, zero spinner)
- Zoom/pan et swipe tactile dans la visionneuse plein ecran
- Paiement par QR code marchand (Wave, Orange Money, MTN Money, Moov Money) : le client scanne, paie
  hors-app, declare "j'ai paye", l'organisateur valide manuellement
- Telechargement : liens individuels + zip complet + QR code de retour, valables indefiniment tant
  que la commande est payee (pas de session a usage unique)
- Retour automatique a la galerie apres 90s d'inactivite sur l'ecran de telechargement (usage borne)

**Cote organisateur** (dashboard admin, JWT)
- Creation/gestion d'evenements (nom, date, lieu, grille tarifaire)
- Upload batch de photos (lots de 10, jusqu'a 500 Mo par lot) avec generation automatique de
  miniature (400px) + preview (1600px) + conservation de l'original intact (aucune perte de qualite,
  reserve au telechargement post-achat)
- **Dossier surveille** : ingestion automatique par polling d'un dossier local (ex: carte SD d'un
  appareil photo copiee sur le PC), sans upload manuel
- Suppression de photos individuelles (bloquee si la photo appartient deja a une commande payee)
- Vue "personnes detectees" identique cote invite, avec vignettes recadrees sur le visage (pas la
  photo entiere) pour identifier chaque groupe d'un coup d'oeil
- Configuration des moyens de paiement par evenement (numero marchand + image QR)
- Confirmation manuelle des commandes en attente de verification
- Statistiques (photos, ventes, revenu par jour) + **historique complet des commandes exportable en
  CSV**
- **Notifications push (PWA)** : alerte sur le telephone de l'organisateur des qu'un client declare
  avoir paye, sans app mobile separee
- Creation de comptes photographe (role limite) par un admin

## Stack technique

| Composant | Choix |
|---|---|
| Backend | FastAPI (async), SQLAlchemy 2.0 (asyncpg), Alembic |
| Base de donnees | PostgreSQL + [pgvector](https://github.com/pgvector/pgvector) (embeddings faciaux, index HNSW) |
| Reconnaissance faciale | [InsightFace](https://github.com/deepinsight/insightface) (buffalo_l), GPU (CUDA) avec repli CPU automatique |
| Clustering | scikit-learn DBSCAN (distance cosinus) |
| Stockage objets | S3-compatible : MinIO en local, Cloudflare R2 en production (bucket prive, URLs presignees) |
| Frontend | Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS |
| Animations | Framer Motion |
| Virtualisation galerie | react-window |
| Notifications push | Web Push (VAPID) + service worker, PWA installable |
| Reverse proxy | nginx |
| Orchestration locale | Docker Compose |
| Exposition publique (dev/self-host) | Cloudflare Tunnel (quick tunnel) |

## Architecture

```
                         ┌──────────────┐
   invite / organisateur │    nginx     │  reverse proxy (port 80)
   ────────────────────► │  /api  → back│
                         │  /     → front│
                         └──────┬───────┘
                                │
                 ┌──────────────┼───────────────┐
                 ▼                              ▼
        ┌─────────────────┐           ┌──────────────────┐
        │  frontend        │           │  backend          │
        │  Next.js 14      │           │  FastAPI (async)  │
        └─────────────────┘           └─────────┬─────────┘
                                                   │
                    ┌──────────────────────────────┼───────────────────────┐
                    ▼                              ▼                       ▼
           ┌─────────────────┐          ┌──────────────────┐   ┌─────────────────────┐
           │  PostgreSQL      │          │  Stockage S3      │   │  InsightFace (GPU)   │
           │  + pgvector       │          │  (MinIO / R2)      │   │  detection + embed.   │
           └─────────────────┘          └──────────────────┘   └─────────────────────┘
```

Flux d'une photo, de l'upload a la revente :

1. **Ingestion** — upload manuel (batch admin) ou automatique (dossier surveille) → validation
   (type, taille) → generation thumbnail (400px) + preview (1600px) → upload de l'original +
   des deux derives vers le stockage objet → ligne `Photo` en base (`indexing_status=pending`).
2. **Indexation** (tache de fond, parallelisme borne) — telechargement de l'original, detection de
   visages (InsightFace), un embedding 512-d par visage detecte, ecriture dans `face_embeddings`
   (pgvector). Seul le calcul GPU est serialise (verrou global) ; le reseau (storage, DB) se
   recouvre entre plusieurs photos.
3. **Recherche** — un invite prend un selfie → un embedding est calcule → comparaison par similarite
   cosinus contre tous les embeddings de l'evenement → photos correspondantes renvoyees, triees.
4. **Groupage** — DBSCAN sur tous les embeddings d'un evenement (metrique cosinus) forme des groupes
   de visages similaires ; un visage sans voisin forme son propre groupe a une photo (jamais
   d'exclusion silencieuse).
5. **Panier → commande → paiement** — le client scanne un QR marchand, paie hors-app, declare
   "j'ai paye" (`AWAITING_CONFIRMATION`) → notification push a l'organisateur → validation manuelle
   → SMS + acces telechargement.
6. **Telechargement** — URLs presignees a expiration courte generees a la demande (jamais stockees),
   zip genere a la volee, QR code permanent vers la page de telechargement.

## Demarrage rapide

Prerequis : Docker Desktop (avec support GPU NVIDIA si vous voulez l'acceleration InsightFace ;
un repli CPU automatique fonctionne sans GPU, plus lent).

```bash
git clone https://github.com/CheickSid27/MY-FACE.git
cd MY-FACE
cp .env.example .env
# Ajustez .env si besoin — les valeurs par defaut fonctionnent en local (MinIO + Postgres local)
docker compose up --build
```

- Frontend : http://localhost:3000
- Backend (docs interactives Swagger) : http://localhost:8000/docs
- Console MinIO : http://localhost:9001

Le premier demarrage applique les migrations Alembic et cree le compte admin initial
(`INITIAL_ADMIN_EMAIL` / `INITIAL_ADMIN_PASSWORD` dans `.env`).

**Notes d'exploitation locale** (voir [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) pour le detail) :
- Apres avoir recree `backend` ou `frontend`, redemarrez `nginx` (`docker restart <container>
  nginx`) : nginx met en cache la resolution DNS de ses upstreams au demarrage.
- Le dossier surveille attend un sous-dossier par evenement dans `./watched-photos/<event_id>/`
  (chemin hote, mappe sur `/watched` dans le conteneur).

## Variables d'environnement

Voir [.env.example](.env.example) pour la liste complete et commentee. Points notables :

- `DATABASE_URL` — Postgres local par defaut ; compatible Neon (serverless) en utilisant
  l'endpoint **direct**, pas le pooler PgBouncer (incompatible avec les requetes preparees
  d'asyncpg).
- `STORAGE_BACKEND` — `local` (MinIO) ou `supabase`. Le support S3-compatible generique
  (`S3_ENDPOINT_URL` + credentials) couvre aussi Cloudflare R2 sans code specifique.
- `PAYMENT_PROVIDER` — `manual` par defaut (aucun operateur reel branche, section paiement pilotee
  par QR marchand + validation humaine). Les adaptateurs Wave/Orange Money/MTN/Moov existent en
  squelette et levent une erreur explicite tant qu'aucune cle API reelle n'est fournie.
- `VAPID_*` — necessaires pour les notifications push admin ; voir
  [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md#notifications-push-vapid) pour generer une paire de cles.
- `WATCHED_FOLDER_*` — configuration du dossier surveille (ingestion automatique).

## Structure du projet

```
backend/
  app/
    core/          # config (pydantic-settings), base de donnees, securite (JWT, hash)
    models/        # SQLAlchemy ORM (User, Event, Photo, FaceEmbedding, Order, ...)
    schemas/       # Pydantic (requetes/reponses API)
    routers/       # endpoints FastAPI par domaine (auth, events, photos, faces, cart, payments, ...)
    services/      # logique metier reutilisable (storage, thumbnails, face_recognition,
                    # face_indexing, folder_watcher, push_notifications, payments, sms, ...)
  alembic/versions/ # migrations
  tests/            # pytest, Postgres reel (pas de mock DB)
frontend/
  app/              # Next.js App Router (pages invite + admin)
  components/       # composants React (gallery, scan, upload, admin, payments, icons)
  lib/              # client API, auth, animations
  types/            # types TypeScript partages (miroir des schemas Pydantic)
nginx/              # reverse proxy (config + Dockerfile)
docs/               # documentation technique detaillee
```

## Tests

```bash
docker compose exec backend pytest
```

La base `myface_test` est creee automatiquement au premier demarrage du conteneur `db` (voir
`backend/docker/init-test-db.sql`). Les tables sont creees/supprimees par les fixtures pytest a
chaque run, contre un vrai Postgres — pas de mock de la base de donnees.

## Documentation complementaire

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — architecture detaillee, modele de donnees, choix
  techniques et leurs justifications
- [docs/API.md](docs/API.md) — reference complete des endpoints REST par domaine
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — deploiement local/self-hosted (Docker Compose, Neon,
  Cloudflare R2, Cloudflare Tunnel, generation des cles VAPID)
- [docs/MYFACE_cahier_des_charges_v2.1.md](docs/MYFACE_cahier_des_charges_v2.1.md) — cahier des
  charges produit original

## Limites connues / non branche

- **Aucun operateur Mobile Money n'a d'API reellement integree** (Wave, Orange Money, MTN Money,
  Moov Money) : le paiement fonctionne via QR marchand statique + validation manuelle organisateur,
  qui est la vraie solution retenue (pas une simulation en attendant mieux).
- **Conformite ARTCI** (donnees biometriques, droit ivoirien) non verifiee formellement — a traiter
  avant tout lancement public a grande echelle.
- **Tunnel Cloudflare "quick"** (sans compte) genere une URL ephemere qui change a chaque
  redemarrage du conteneur `tunnel-app` ; un nom de domaine + tunnel nomme est necessaire pour une
  URL stable en production.
- Pas de suite CI automatisee configuree dans ce depot (tests a lancer manuellement).
