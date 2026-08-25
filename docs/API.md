# Reference API

Documentation interactive complete (schemas de requete/reponse, essai en direct) generee
automatiquement par FastAPI : **http://localhost:8000/docs** (Swagger UI) ou `/redoc`.

Ce document donne une vue d'ensemble organisee par domaine, avec le niveau d'authentification
requis pour chaque endpoint.

Legende : 🔒 = JWT organisateur requis (`Authorization: Bearer <token>`) · 🔒👑 = JWT + role `admin`
· 🌐 = public (aucune authentification)

## Auth — `/auth`

| Methode | Route | Description |
|---|---|---|
| POST | `/auth/login` | Connexion, renvoie `access_token` + `refresh_token` |
| POST | `/auth/refresh` | Renouvelle un `access_token` a partir d'un `refresh_token` |
| GET 🔒 | `/auth/me` | Profil de l'utilisateur connecte |

## Evenements — `/events`

| Methode | Route | Description |
|---|---|---|
| POST 🔒 | `/events` | Cree un evenement (nom, date, lieu, grille tarifaire) |
| GET 🔒 | `/events` | Liste des evenements de l'organisateur connecte |
| GET 🔒 | `/events/{id}` | Detail d'un evenement (proprietaire uniquement) |
| GET 🌐 | `/events/{id}/public` | Vue publique (accueil borne/invite, sans donnees sensibles) |
| PATCH 🔒 | `/events/{id}` | Met a jour un evenement |
| DELETE 🔒 | `/events/{id}` | Supprime un evenement et tout son contenu (cascade) |
| GET 🔒 | `/events/{id}/clusters` | Groupes de visages (admin, DBSCAN + vignettes recadrees) |
| GET 🌐 | `/events/{id}/clusters/public` | Meme groupage, expose au bouton invite "Trouver mon visage" |
| GET 🔒 | `/events/{id}/watched-folder` | Etat du dossier surveille (chemin + fichiers en cours/ingeres/erreur) |
| GET 🔒 | `/events/{id}/payment-methods` | Moyens de paiement configures pour l'evenement |
| PUT 🔒 | `/events/{id}/payment-methods/{method}` | Configure/modifie un moyen de paiement (numero + image QR) |
| DELETE 🔒 | `/events/{id}/payment-methods/{method}` | Retire un moyen de paiement |

## Photos — racine + `/events/{id}/photos`

| Methode | Route | Description |
|---|---|---|
| POST 🔒 | `/photos/upload?event_id=` | Upload batch (multipart, plusieurs fichiers) |
| GET 🌐 | `/events/{id}/photos` | Liste paginee des photos d'un evenement |
| DELETE 🔒 | `/photos/{id}` | Supprime une photo (bloque si deja vendue) |

## Reconnaissance faciale — `/faces`

| Methode | Route | Description |
|---|---|---|
| POST 🌐 | `/faces/scan?event_id=` | Envoie un selfie, renvoie les photos correspondantes triees par similarite |
| GET 🌐 | `/faces/status/{photo_id}` | Statut d'indexation d'une photo (`pending`/`processing`/`done`/`failed`) |

## Panier — `/cart`

| Methode | Route | Description |
|---|---|---|
| POST 🌐 | `/cart/add` | Ajoute une photo au panier (cree la session si besoin) |
| GET 🌐 | `/cart/{session_id}` | Contenu du panier + calcul du prix (remises incluses) |
| DELETE 🌐 | `/cart/{item_id}` | Retire un item du panier |

## Paiement — `/payments`

| Methode | Route | Description |
|---|---|---|
| POST 🌐 | `/payments/init` | Cree une commande a partir d'un panier (QR marchand si `payment_method` fourni) |
| POST 🌐 | `/payments/{id}/mark-paid` | Le client declare avoir paye → statut `awaiting_confirmation` + notification push organisateur |
| GET 🌐 | `/payments/status/{id}` | Statut de paiement (utilise en polling par le frontend) |
| POST 🌐 | `/payments/webhook` | Webhook operateur reel (signature HMAC), pour quand une API Mobile Money sera branchee |

## Telechargement — `/download`

| Methode | Route | Description |
|---|---|---|
| GET 🌐 | `/download/{order_id}` | Liens presignes individuels (commande payee uniquement) |
| GET 🌐 | `/download/{order_id}/zip` | Toutes les photos de la commande en un seul zip |
| GET 🌐 | `/download/{order_id}/qr.png` | QR code permanent vers la page de telechargement |

## Notifications push — `/notifications`

| Methode | Route | Description |
|---|---|---|
| GET 🌐 | `/notifications/vapid-public-key` | Cle publique VAPID (necessaire cote navigateur pour s'abonner) |
| POST 🔒 | `/notifications/subscribe` | Enregistre un abonnement Web Push pour l'organisateur connecte |
| POST 🔒 | `/notifications/unsubscribe` | Retire un abonnement |

## Administration — `/admin`

| Methode | Route | Description |
|---|---|---|
| GET 🔒 | `/admin/events/{id}/stats` | Statistiques (photos, ventes, revenu par jour) |
| GET 🔒 | `/admin/events/{id}/orders` | Historique complet des commandes (filtrable par statut) |
| POST 🔒 | `/admin/orders/{id}/confirm` | Confirme/rejette une commande en attente de verification |
| GET 🔒👑 | `/admin/users` | Liste des utilisateurs (reserve role `admin`) |
| POST 🔒👑 | `/admin/users` | Cree un compte (organisateur ou photographe) |
| DELETE 🔒👑 | `/admin/users/{id}` | Supprime un utilisateur (refuse s'il possede des evenements) |

## Conventions

- Toutes les erreurs suivent le format FastAPI standard : `{"detail": "message explicite en francais"}`.
- Les identifiants sont des UUID v4.
- Les dates sont en ISO 8601, toujours en UTC.
- Aucun endpoint ne renvoie jamais d'URL de stockage statique : les champs `*_url` sont toujours des
  URLs presignees a expiration courte, generees a la demande.
