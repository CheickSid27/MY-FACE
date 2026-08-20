# MYFACE — Phase 1 : Fondations Web App

Voir [docs/MYFACE_cahier_des_charges_v2.1.md](docs/MYFACE_cahier_des_charges_v2.1.md) pour la vision produit complete et la roadmap.

## Ce qui est fonctionnel dans cette Phase 1

- Monorepo : `frontend` (Next.js/TypeScript/Tailwind), `backend` (FastAPI async), `nginx`, `docker-compose`
- Auth admin JWT (login, refresh, `/auth/me`) branchee sur Postgres reel
- CRUD `events` complet (create/list/get/patch/delete), protege par JWT + ownership
- Endpoint public `GET /events/{id}/public` pour l'ecran Accueil borne/invite (sans auth)
- Upload batch de photos avec validation (type MIME, taille max 25 Mo), generation de miniatures via Pillow, stockage reel (MinIO en dev)
- Ecran Accueil (`/event/{id}`) et Galerie complete virtualisee (`/event/{id}/gallery`, react-window), responsive borne/mobile/desktop
- Dashboard admin : login, liste/creation d'evenements, upload batch, suppression
- Tests backend (pytest + Postgres reel, pas de mock de la DB) : auth, events, photos
- Migration Alembic initiale + script de seed du compte admin

## Ce qui N'EST PAS branche (a signaler explicitement)

- **Supabase** : `STORAGE_BACKEND=local` par defaut -> les photos sont stockees sur MinIO (S3-compatible, local, dans docker-compose). Des que vous me fournissez `SUPABASE_URL` et `SUPABASE_SERVICE_ROLE_KEY`, je bascule `STORAGE_BACKEND=supabase` (l'implementation `SupabaseStorageService` existe deja dans [backend/app/services/storage.py](backend/app/services/storage.py) mais leve une erreur explicite tant que les credentials manquent — jamais de fallback silencieux).
- Reconnaissance faciale, panier, paiement, SMS, dashboard analytics : Phases 2 a 4, non commences.

## Demarrage

1. Copier `.env.example` en `.env` et ajuster si besoin (les valeurs par defaut fonctionnent en local).
2. Lancer l'infra :

```bash
docker compose up --build
```

3. Frontend : http://localhost:3000 — Backend : http://localhost:8000/docs — MinIO console : http://localhost:9001

Le premier demarrage du backend applique les migrations Alembic et cree le compte admin initial (`INITIAL_ADMIN_EMAIL` / `INITIAL_ADMIN_PASSWORD` dans `.env`).

## Tests backend

```bash
docker compose exec backend pytest
```

(La base `myface_test` est creee automatiquement au premier demarrage du conteneur `db` via `backend/docker/init-test-db.sql`. Les tables sont creees/supprimees par les fixtures pytest a chaque run.)
