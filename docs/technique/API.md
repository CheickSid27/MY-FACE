# Reference API

Mise a jour : 22 octobre 2026 (liste tiree des routes reelles du serveur).

Documentation interactive complete (schemas de requete/reponse, essai en direct) generee
automatiquement par FastAPI : **http://localhost:8000/docs** (Swagger UI) ou `/redoc`, en
developpement seulement (fermee en production, `ENVIRONMENT=production`). En production, l'API est
servie sous `https://app.myfaceci.online/api/...` (nginx retire le prefixe `/api`).

Ce document donne une vue d'ensemble organisee par domaine, avec le niveau d'authentification
requis pour chaque endpoint.

Legende : 🔒 = JWT requis (`Authorization: Bearer <token>`) · 🔒👑 = JWT + role `admin`
· 🌐 = public (aucune authentification) · 🌐🔑 = public, mais reconnait l'utilisateur connecte s'il
y en a un (organisateur qui consulte sa propre galerie, par exemple)

**Droits** : un photographe gere uniquement ses evenements ; un admin gere tous les evenements
(tous organisateurs). **Mode borne** : les endpoints publics marques `kiosk_token` acceptent le
jeton borne de l'evenement en parametre ; s'il est valide, les apercus grand format sont servis
nets, sinon filigranes (telephone d'un invite). **Adresse e-mail non confirmee** : un photographe
inscrit seul est bloque (403) sur les actions de son espace tant qu'il n'a pas confirme son
adresse ; sans confirmation en `UNVERIFIED_ACCOUNT_TTL_MINUTES` (5 min), l'inscription est
annulee et tout est supprime.

## Auth, `/auth`

| Methode | Route | Description |
|---|---|---|
| POST 🌐 | `/auth/register` | Inscription libre d'un photographe (nom, e-mail, telephone, mot de passe) ; envoie le lien de confirmation |
| POST 🌐 | `/auth/verify-email` | Confirme l'adresse a partir du jeton du lien (valable 5 min) |
| POST 🔒 | `/auth/resend-verification` | Renvoie le lien de confirmation (limite par adresse) |
| POST 🌐 | `/auth/login` | Connexion, renvoie `access_token` + `refresh_token` |
| POST 🌐 | `/auth/refresh` | Renouvelle un `access_token` a partir d'un `refresh_token` |
| POST 🌐 | `/auth/forgot-password` | Envoie un lien de reinitialisation (reponse identique que l'adresse existe ou non) |
| POST 🌐 | `/auth/reset-password` | Nouveau mot de passe a partir du jeton du lien |
| GET 🔒 | `/auth/me` | Profil ; `must_verify_email` et `verification_deadline` (heure d'annulation, `null` pour les comptes anciens) |
| PATCH 🔒 | `/auth/me` | Modifie le profil (nom, studio, telephone, ville) |
| POST 🔒 | `/auth/password` | Change son propre mot de passe ; deconnecte les autres appareils |
| POST 🔒 | `/auth/me/avatar` | Photo de profil (recadree en carre 512 px, sans EXIF) |
| DELETE 🔒 | `/auth/me/avatar` | Retire la photo de profil |
| GET 🌐 | `/auth/avatars/{user_id}?v=` | Sert la photo de profil (affichee aux invites a cote du nom du photographe) |
| GET 🔒 | `/auth/me/payout` | Compte de versement des ventes en ligne (masque) |
| PUT 🔒 | `/auth/me/payout` | Active les ventes en ligne : Wave, Orange, MTN ou banque (RIB) ; cree ou met a jour le sous-compte Paystack |
| DELETE 🔒 | `/auth/me/payout` | Desactive les ventes en ligne |

## Evenements, `/events`

| Methode | Route | Description |
|---|---|---|
| POST 🔒 | `/events` | Cree un evenement (nom, date, lieu, grille tarifaire), son code court et son sous-dossier surveille ; un seul evenement Decouverte (gratuit) par compte |
| GET 🔒 | `/events` | Evenements de l'organisateur ; tous les evenements (+ `organizer_email`) pour un admin |
| GET 🌐 | `/events/code/{code}` | Code court (« K7M2-QX9P », casse et tiret indifferents) → `{id}` ; 404 si inconnu ; 30 codes faux par 10 min et par adresse, 60 requetes/min dans nginx |
| GET 🔒 | `/events/{id}` | Detail, avec `short_code`, `guest_url` (`/e/CODE`) et `kiosk_url` construits sur `APP_BASE_URL` |
| GET 🌐🔑 | `/events/{id}/public` | Vue publique (dont `short_code`, nom du photographe, galerie protegee ou non) ; `?kiosk_token=` → `is_kiosk` calcule serveur (jeton jamais renvoye) |
| POST 🌐 | `/events/{id}/unlock` | Mot de passe de la galerie → jeton d'acces (10 essais par 10 min) |
| PATCH 🔒 | `/events/{id}` | Met a jour nom, date, lieu, grille tarifaire, cadre, especes, filigrane, mot de passe de galerie |
| DELETE 🔒 | `/events/{id}` | Supprime l'evenement et ses fichiers ; **409** s'il a des commandes payees |
| GET 🔒 | `/events/{id}/qr.png?kind=guest\|kiosk` | QR code du lien invite (adresse courte) ou du lien borne (PNG) |
| GET 🔒 | `/events/{id}/indexing` | Etat de l'indexation faciale (`pending`, `processing`, `done`, `failed`, `faces`) |
| POST 🔒 | `/events/{id}/reindex` | Relance l'indexation des photos en echec/non terminees → `{queued}` (202) |
| GET 🔒 | `/events/{id}/clusters` | Groupes de visages (organisateur, apercus nets) |
| GET 🌐🔑 | `/events/{id}/clusters/public` | Meme groupage pour « Trouver mon visage » (`kiosk_token`) |
| GET 🔒 | `/events/{id}/watched-folder` | Dossier surveille du PC de la borne (equipe MYFACE) |
| GET 🌐 | `/events/{id}/payment-methods` | Moyens de paiement directs configures (QR marchands) |
| PUT 🔒 | `/events/{id}/payment-methods/{method}` | Configure un QR marchand (`phone_number` + `qr_image`) |
| DELETE 🔒 | `/events/{id}/payment-methods/{method}` | Retire un moyen de paiement |

Grille tarifaire (`pricing`) :

```json
{
  "unit_price": 1000,
  "currency": "XOF",
  "packs": [{"count": 10, "price": 8000}],
  "discounts": [{"min_quantity": 20, "percent": 15}],
  "print_unit_price": 200,
  "print_bundle_price": 700,
  "offert": false
}
```

Lots : `count` >= 2, tailles uniques. Remises : `min_quantity` >= 2, `0 < percent < 100`, seuils
uniques. Les lots s'appliquent d'abord (plus grand en premier), puis la meilleure remise.
`print_bundle_price` : prix « photo + tirage » (borne). `offert` : photos offertes par l'organisateur.

## Packs du service photographe, `/packs` et `/events/{id}/pack`

| Methode | Route | Description |
|---|---|---|
| GET 🌐 | `/packs` | Catalogue : Decouverte (gratuit, 10 photos), Evenement (10 000 F, 500 photos), Pro (25 000 F, 2 000 photos), Sur mesure |
| GET 🔒 | `/packs/payment-info` | Numeros Mobile Money de MYFACE pour payer un pack a la main |
| GET 🔒 | `/events/{id}/pack` | Pack de l'evenement, photos restantes, options, packs superieurs (montant du = difference) |
| POST 🔒 | `/events/{id}/pack-purchases` | Declare un paiement Mobile Money (reference de transaction), valide a la main par l'equipe |
| POST 🔒 | `/events/{id}/pack-purchases/paystack` | Paiement en ligne d'un pack → `authorization_url` Paystack |
| POST 🔒 | `/pack-purchases/{id}/paystack/verify` | Verifie le paiement aupres de Paystack au retour et active le pack |
| POST 🔒 | `/pack-purchases/{id}/cancel` | Annule une declaration en attente |
| GET 🔒👑 | `/admin/pack-purchases` | Paiements de packs a verifier |
| POST 🔒👑 | `/admin/pack-purchases/{id}/approve` · `/reject` | Valide ou refuse (avec note) |
| PUT 🔒👑 | `/admin/events/{id}/pack` | Change le pack d'un evenement (ou limite sur mesure) |
| GET/PUT 🔒👑 | `/admin/settings/pack-payment` | Numeros de paiement des packs |

Au-dela de la limite du pack, chaque photo envoyee est refusee avec le message « Limite du pack … »
(l'interface ouvre alors la proposition de pack superieur).

## Photos, racine + `/events/{id}/photos`

| Methode | Route | Description |
|---|---|---|
| POST 🔒 | `/photos/upload?event_id=` | Upload par lots (multipart) : JPEG, PNG, WebP ou RAW (CR2, CR3, NEF, ARW, DNG, RAF...), 70 Mo max par photo ; RAW garde + JPEG pleine resolution ; un nom de fichier deja present dans l'evenement (majuscules et minuscules confondues) est refuse |
| GET 🌐🔑 | `/photos/{id}/faces` | Visages de la photo, de gauche a droite : vignette (`face_url`) et groupe (`cluster_id`), pour les bulles de la visionneuse ; memes droits que la galerie (`kiosk_token`, `access`) |
| GET 🌐🔑 | `/events/{id}/photos` | Liste paginee (`page`, `page_size` <= 200, `kiosk_token`, `access` pour une galerie protegee) |
| DELETE 🔒 | `/photos/{id}` | Supprime une photo et tous ses fichiers derives (409 si deja vendue) |
| POST 🔒 | `/photos/bulk-delete` | Supprime plusieurs photos d'un evenement d'un coup (`event_id`, `photo_ids`, 2 000 max) : selection, ou toutes les photos d'une personne (groupe de visages, ou retrouvee par sa photo) ; les photos deja vendues sont gardees et listees (`kept_sold`) |

## Reconnaissance faciale, `/faces`

| Methode | Route | Description |
|---|---|---|
| POST 🌐🔑 | `/faces/scan?event_id=` | Selfie (+ `consent=true`), renvoie les photos correspondantes triees (`kiosk_token`) ; le selfie n'est jamais enregistre |
| GET 🌐 | `/faces/status/{photo_id}` | Statut d'indexation d'une photo |

## Panier, `/cart`

| Methode | Route | Description |
|---|---|---|
| POST 🌐 | `/cart/add` | Ajoute une photo au panier (cree la session si besoin) |
| POST 🌐 | `/cart/add-bulk` | Ajoute plusieurs photos en une requete (<= 500) |
| GET 🌐 | `/cart/{session_id}` | Contenu du panier + calcul du prix (lots, remises, impression) |
| PATCH 🌐 | `/cart/{item_id}` | Coche/decoche le tirage papier ; cocher exige `kiosk_token` (403 sinon) |
| DELETE 🌐 | `/cart/{item_id}` | Retire un item du panier |

## Paiement, `/payments`

| Methode | Route | Description |
|---|---|---|
| POST 🌐 | `/payments/init` | Cree une commande depuis un panier (voir ci-dessous) |
| POST 🌐 | `/payments/offert` | Commande d'un evenement en photos offertes (total 0, payee d'office) |
| POST 🌐 | `/payments/{id}/mark-paid` | Le client declare avoir paye (QR marchand) → `awaiting_confirmation` + notification |
| GET 🌐 | `/payments/status/{id}` | Statut (polling) ; pour Paystack, verifie la transaction aupres de Paystack |
| GET 🌐 | `/payments/paystack-qr.png?url=` | QR code de la page de paiement Paystack (borne) ; n'accepte que des adresses Paystack |
| GET 🌐 | `/payments/paystack/banks` | Banques et operateurs Mobile Money acceptes pour les versements (Cote d'Ivoire) |
| POST 🌐 | `/payments/paystack/webhook` | Notification Paystack (signature HMAC-SHA512 `x-paystack-signature`) : commandes et packs |
| POST 🌐 | `/payments/webhook` | Webhook operateur generique (signature HMAC `X-Signature`) |

`/payments/init` :

```json
{"session_id": "...", "contact_phone": "+2250701020304", "payment_method": "paystack"}
```

- `payment_method` **obligatoire** :
  - `paystack` : paiement en ligne (Wave, Orange Money, MTN, carte) pour les evenements de MYFACE
    et ceux des photographes qui ont active leurs versements. Le montant est partage par Paystack :
    100 % au photographe (sous-compte, `bearer: subaccount`, frais Paystack a sa charge), 0 % pour
    MYFACE. Reponse : `authorization_url`.
  - un moyen QR configure pour l'evenement (paiement direct au photographe, confirme par lui) ;
  - `cash` : evenement avec especes activees **et** `kiosk_token` valide de la borne (403 sinon).
- `contact_phone` : numero international, valide selon le format reel du pays et stocke en E.164
  (voir `GET /meta/phone-countries`).
- Les montants Paystack sont envoyes en centimes (x100) ; un paiement n'est jamais active sans
  verification aupres de Paystack.

Statuts de commande : `pending` (a payer) → `awaiting_confirmation` (le client dit avoir paye) →
`success` / `failed` (rejetee). `cancelled` : jamais payee dans le delai
(`ORDER_PENDING_TTL_MINUTES`) ou annulee par l'organisateur.

GeniusPay : routes `/payments/geniuspay/*` montees seulement si GeniusPay est configure (abandonne
au profit de Paystack, code garde).

## Telechargement, `/download`

| Methode | Route | Description |
|---|---|---|
| GET 🌐 | `/download/{order_id}` | Par photo : `url` (original, telechargement force sous son nom) + `thumbnail_url` |
| GET 🌐 | `/download/{order_id}/zip` | Toutes les photos de la commande, zip envoye au fil de l'eau |
| GET 🌐 | `/download/{order_id}/qr.png` | QR code vers la page de telechargement (valable tant que les photos sont en ligne) |
| POST 🌐🔑 | `/download/{order_id}/printed` | Enregistre l'impression des tirages : `kiosk_token` de la borne ou organisateur connecte |

## Espace MYFACE Pro, `/workspace`

| Methode | Route | Description |
|---|---|---|
| GET 🔒 | `/workspace/summary` | Accueil : evenement du moment, chiffres du jour, liste « A faire » (paiements a confirmer, evenement sans moyen de paiement...) |
| GET 🔒 | `/workspace/orders?view=to_confirm\|paid&days=` | Ventes de tous ses evenements |
| GET 🔒 | `/workspace/activity` | Fil des notifications |

## Statistiques, `/activity`

| Methode | Route | Description |
|---|---|---|
| GET 🔒 | `/activity` | Journal des actions (inscriptions, connexions, evenements, photos, selfies, telechargements, packs, comptes) ; filtres `action`, `event_id`, `start`, `end`, `q`, `page` (50 par page) ; compteurs par action. Equipe : tout ; photographe : ses actions et celles qui touchent ses evenements |
| GET 🔒 | `/activity/export.csv` | Meme filtres, CSV pour Excel (separateur `;`, 50 000 lignes max) |

## Donnees de reference, `/meta`

| Methode | Route | Description |
|---|---|---|
| GET 🌐 | `/meta/phone-countries` | Pays acceptes (indicatif, format du numero national, exemple), Cote d'Ivoire en premier |
| GET 🌐 | `/meta/features` | Fonctions actives sur ce serveur (paiement Paystack...) |

## Notifications push, `/notifications`

| Methode | Route | Description |
|---|---|---|
| GET 🌐 | `/notifications/vapid-public-key` | Cle publique VAPID (base64url brute) |
| POST 🔒 | `/notifications/subscribe` | Enregistre un abonnement Web Push |
| POST 🔒 | `/notifications/unsubscribe` | Retire un abonnement |

Une notification (vibration, urgence haute) par paiement a confirmer, par vente payee en ligne et,
pour l'equipe, par pack paye ou a verifier.

## Administration, `/admin`

| Methode | Route | Description |
|---|---|---|
| GET 🔒 | `/admin/events/{id}/stats` | Statistiques de l'evenement (photos, ventes par statut, revenu par jour) |
| GET 🔒 | `/admin/events/{id}/orders` | Historique des commandes (`?order_status=`) |
| GET 🔒 | `/admin/orders/{id}` | Fiche/recu detaille de la commande |
| POST 🔒 | `/admin/orders/{id}/confirm` | `{"approved": true}` valide ; `false` rejette |
| POST 🔒 | `/admin/orders/{id}/cancel` | Annule une commande jamais payee |
| GET 🔒👑 | `/admin/users` | Liste des comptes |
| POST 🔒👑 | `/admin/users` | Cree un compte (adresse consideree comme confirmee) |
| PATCH 🔒👑 | `/admin/users/{id}` | Suspend / reactive un compte |
| DELETE 🔒👑 | `/admin/users/{id}` | Supprime un compte (refuse s'il possede des evenements, ou si c'est soi-meme) |
| PUT/DELETE 🔒👑 | `/admin/users/{id}/payout-code` | Code de sous-compte Paystack cree a la main |
| GET 🔒👑 | `/admin/retention` | Etat de la conservation des donnees (90 jours pour les photos et visages) |
| POST 🔒👑 | `/admin/retention/run` | Lance la suppression des donnees arrivees a echeance |
| PUT 🔒👑 | `/admin/events/{id}/retention` | Exempte ou non un evenement de la suppression automatique |

## Conventions

- Toutes les erreurs suivent le format FastAPI standard : `{"detail": "message explicite en francais"}`
  (liste de details pour une erreur de validation 422).
- Les identifiants sont des UUID v4 ; les evenements ont en plus un code court de 8 caracteres.
- Les dates sont en ISO 8601, toujours en UTC.
- Aucun endpoint ne renvoie jamais d'URL de stockage statique : les champs `*_url` de fichiers sont
  toujours des URLs presignees a expiration courte, generees a la demande.
