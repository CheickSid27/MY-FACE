# Reference API

Documentation interactive complete (schemas de requete/reponse, essai en direct) generee
automatiquement par FastAPI : **http://localhost:8000/docs** (Swagger UI) ou `/redoc`.

Ce document donne une vue d'ensemble organisee par domaine, avec le niveau d'authentification
requis pour chaque endpoint.

Legende : 🔒 = JWT organisateur requis (`Authorization: Bearer <token>`) · 🔒👑 = JWT + role `admin`
· 🌐 = public (aucune authentification)

**Droits** : un photographe gere uniquement ses evenements ; un admin gere tous les evenements
(tous organisateurs). **Mode borne** : les endpoints publics marques `kiosk_token` acceptent le
jeton borne de l'evenement en parametre ; s'il est valide, les apercus grand format sont servis
nets, sinon filigranes (telephone d'un invite).

## Auth — `/auth`

| Methode | Route | Description |
|---|---|---|
| POST | `/auth/login` | Connexion, renvoie `access_token` + `refresh_token` |
| POST | `/auth/refresh` | Renouvelle un `access_token` a partir d'un `refresh_token` |
| GET 🔒 | `/auth/me` | Profil de l'utilisateur connecte |
| POST 🔒 | `/auth/password` | Change son propre mot de passe (`current_password`, `new_password` >= 8 caracteres) |

## Evenements — `/events`

| Methode | Route | Description |
|---|---|---|
| POST 🔒 | `/events` | Cree un evenement (nom, date, lieu, grille tarifaire) et son sous-dossier surveille |
| GET 🔒 | `/events` | Evenements de l'organisateur ; tous les evenements (+ `organizer_email`) pour un admin |
| GET 🔒 | `/events/{id}` | Detail, avec `guest_url` et `kiosk_url` construits sur `APP_BASE_URL` |
| GET 🌐 | `/events/{id}/public` | Vue publique ; `?kiosk_token=` → `is_kiosk` calcule serveur (jeton jamais renvoye) |
| PATCH 🔒 | `/events/{id}` | Met a jour nom, date, lieu, grille tarifaire (remplacee en entier), cadre, especes |
| DELETE 🔒 | `/events/{id}` | Supprime l'evenement et ses fichiers ; **409** s'il a des commandes payees |
| GET 🔒 | `/events/{id}/qr.png?kind=guest\|kiosk` | QR code du lien invite ou du lien borne (PNG) |
| GET 🔒 | `/events/{id}/indexing` | Etat de l'indexation faciale (`pending`, `processing`, `done`, `failed`, `faces`) |
| POST 🔒 | `/events/{id}/reindex` | Relance l'indexation des photos en echec/non terminees → `{queued}` (202) |
| GET 🔒 | `/events/{id}/clusters` | Groupes de visages (admin, apercus nets, toujours a jour) |
| GET 🌐 | `/events/{id}/clusters/public` | Meme groupage pour "Trouver mon visage" (`kiosk_token`) |
| GET 🔒 | `/events/{id}/watched-folder` | Etat du dossier surveille (chemin + fichiers en cours/ingeres/erreur) |
| GET 🌐 | `/events/{id}/payment-methods` | Moyens de paiement configures pour l'evenement |
| PUT 🔒 | `/events/{id}/payment-methods/{method}` | Configure un QR marchand (`phone_number` + `qr_image`, image facultative en modification) |
| DELETE 🔒 | `/events/{id}/payment-methods/{method}` | Retire un moyen de paiement |

Grille tarifaire (`pricing`) :

```json
{
  "unit_price": 1000,
  "currency": "XOF",
  "packs": [{"count": 10, "price": 8000}],
  "discounts": [{"min_quantity": 20, "percent": 15}],
  "print_unit_price": 200
}
```

Lots : `count` >= 2, tailles uniques. Remises : `min_quantity` >= 2, `0 < percent < 100`, seuils
uniques. Les lots s'appliquent d'abord (plus grand en premier), puis la meilleure remise.

## Photos — racine + `/events/{id}/photos`

| Methode | Route | Description |
|---|---|---|
| POST 🔒 | `/photos/upload?event_id=` | Upload batch (multipart, plusieurs fichiers) |
| GET 🌐 | `/events/{id}/photos` | Liste paginee (`page`, `page_size` <= 200, `kiosk_token`) |
| DELETE 🔒 | `/photos/{id}` | Supprime une photo et tous ses fichiers derives (409 si deja vendue) |

## Reconnaissance faciale — `/faces`

| Methode | Route | Description |
|---|---|---|
| POST 🌐 | `/faces/scan?event_id=` | Selfie (+ `consent=true`), renvoie les photos correspondantes triees (`kiosk_token`) |
| GET 🌐 | `/faces/status/{photo_id}` | Statut d'indexation d'une photo (`pending`/`processing`/`done`/`failed`) |

## Panier — `/cart`

| Methode | Route | Description |
|---|---|---|
| POST 🌐 | `/cart/add` | Ajoute une photo au panier (cree la session si besoin) |
| POST 🌐 | `/cart/add-bulk` | Ajoute plusieurs photos en une requete (<= 500) |
| GET 🌐 | `/cart/{session_id}` | Contenu du panier + calcul du prix (lots, remises, impression) |
| PATCH 🌐 | `/cart/{item_id}` | Coche/decoche le tirage papier (`print_requested`) ; cocher exige `kiosk_token` (403 sinon) |
| DELETE 🌐 | `/cart/{item_id}` | Retire un item du panier |

## Paiement — `/payments`

| Methode | Route | Description |
|---|---|---|
| POST 🌐 | `/payments/init` | Cree une commande depuis un panier (voir ci-dessous) |
| POST 🌐 | `/payments/{id}/mark-paid` | Le client declare avoir paye → `awaiting_confirmation` + push organisateur (409 si expiree) |
| GET 🌐 | `/payments/status/{id}` | Statut (polling frontend) ; une commande jamais payee trop ancienne passe `cancelled` |
| POST 🌐 | `/payments/webhook` | Webhook operateur generique (signature HMAC `X-Signature`) |
| POST 🌐 | `/payments/geniuspay/init` | Parcours GeniusPay isole (sandbox, sans ecran invite) |
| POST 🌐 | `/payments/geniuspay/webhook` | Webhook GeniusPay (signature `X-Webhook-Signature`) |
| GET 🔒 | `/payments/geniuspay/status/{id}` | Debug sandbox |

`/payments/init` :

```json
{"session_id": "...", "contact_phone": "+2250701020304", "payment_method": "wave"}
```

- `payment_method` **obligatoire** : un moyen QR configure pour l'evenement, ou `cash` (evenement
  avec especes activees **et** `kiosk_token` valide de la borne, 403 sinon). `manual` et
  `geniuspay` sont refuses ici.
- `contact_phone` : numero international, valide selon le format reel du pays et stocke en E.164
  (voir `GET /meta/phone-countries`).

Statuts de commande : `pending` (a payer) → `awaiting_confirmation` (le client dit avoir paye) →
`success` / `failed` (rejetee). `cancelled` : jamais payee dans le delai
(`ORDER_PENDING_TTL_MINUTES`) ou annulee par l'organisateur. `processing` : historique (ancien repli
supprime).

## Telechargement — `/download`

| Methode | Route | Description |
|---|---|---|
| GET 🌐 | `/download/{order_id}` | Par photo : `url` (original, telechargement force sous son nom) + `thumbnail_url` |
| GET 🌐 | `/download/{order_id}/zip` | Toutes les photos de la commande, zip envoye au fil de l'eau |
| GET 🌐 | `/download/{order_id}/qr.png` | QR code permanent vers la page de telechargement |
| POST 🌐/🔒 | `/download/{order_id}/printed` | Enregistre l'impression des tirages (`printed_at`) : `kiosk_token` de la borne ou organisateur connecte |

## Donnees de reference — `/meta`

| Methode | Route | Description |
|---|---|---|
| GET 🌐 | `/meta/phone-countries` | Pays acceptes (indicatif, format du numero national, exemple, aide) — Cote d'Ivoire en premier |

## Notifications push — `/notifications`

| Methode | Route | Description |
|---|---|---|
| GET 🌐 | `/notifications/vapid-public-key` | Cle publique VAPID (necessaire cote navigateur pour s'abonner) |
| POST 🔒 | `/notifications/subscribe` | Enregistre un abonnement Web Push pour l'organisateur connecte |
| POST 🔒 | `/notifications/unsubscribe` | Retire un abonnement |

## Administration — `/admin`

| Methode | Route | Description |
|---|---|---|
| GET 🔒 | `/admin/events/{id}/stats` | Statistiques (photos, ventes par statut dont `orders_cancelled`, revenu par jour) |
| GET 🔒 | `/admin/events/{id}/orders` | Historique des commandes (`?order_status=`), avec `print_count` et `printed_at` |
| GET 🔒 | `/admin/orders/{id}` | Fiche/recu : evenement, liste nominative des photos, tirages, `photos_subtotal`, `prints_total`, `discount_amount`, `download_url` |
| POST 🔒 | `/admin/orders/{id}/confirm` | `{"approved": true}` valide (tout statut non paye, y compris expiree) ; `false` rejette |
| POST 🔒 | `/admin/orders/{id}/cancel` | Annule une commande jamais payee (`pending`/`processing`) |
| GET 🔒👑 | `/admin/users` | Liste des utilisateurs |
| POST 🔒👑 | `/admin/users` | Cree un compte (organisateur ou photographe) |
| DELETE 🔒👑 | `/admin/users/{id}` | Supprime un utilisateur (refuse s'il possede des evenements, ou si c'est soi-meme) |

## Conventions

- Toutes les erreurs suivent le format FastAPI standard : `{"detail": "message explicite en francais"}`
  (liste de details pour une erreur de validation 422).
- Les identifiants sont des UUID v4.
- Les dates sont en ISO 8601, toujours en UTC.
- Aucun endpoint ne renvoie jamais d'URL de stockage statique : les champs `*_url` sont toujours des
  URLs presignees a expiration courte, generees a la demande.
