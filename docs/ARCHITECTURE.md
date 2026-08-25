# Architecture

## Vue d'ensemble

MYFACE est un monorepo avec trois services applicatifs (`backend`, `frontend`, `nginx`) plus
l'infrastructure (Postgres, stockage objet), orchestres par Docker Compose. Le backend est une API
REST stateless (FastAPI, async de bout en bout) ; le frontend est un Next.js App Router qui
consomme cette API. Aucune logique metier ne vit cote nginx : il route uniquement `/api/*` vers le
backend et le reste vers le frontend.

## Modele de donnees

Tables principales (voir `backend/app/models/`) :

| Table | Role |
|---|---|
| `users` | Comptes organisateur/photographe (JWT), role `admin` ou `photographe` |
| `events` | Un evenement = un lien/QR unique (`kiosk_token`), une grille tarifaire (JSON) |
| `photos` | Une photo uploadee : cles de stockage (original/thumbnail/preview), statut d'indexation |
| `face_embeddings` | Un embedding 512-d (pgvector) par visage detecte dans une photo, + bounding box |
| `cart_sessions` / `cart_items` | Panier invite, identifie par un `session_id` (pas de compte requis), TTL |
| `orders` / `order_items` | Commande + snapshot des photos achetees et de leur prix unitaire au moment de l'achat |
| `event_payment_methods` | QR marchand + numero, par evenement et par moyen de paiement |
| `push_subscriptions` | Abonnements Web Push d'un organisateur (PWA), un par navigateur/appareil installe |

Suppressions en cascade au niveau base (`ON DELETE CASCADE`) : supprimer un evenement supprime ses
photos, qui suppriment leurs embeddings ; supprimer une photo non vendue supprime ses lignes de
panier/commande associees. Une photo deja presente dans une commande **payee** (`SUCCESS`) ne peut
pas etre supprimee (verifie explicitement dans `routers/photos.py`) pour ne jamais casser l'acces
post-achat d'un client.

Le bucket de stockage objet est **prive** : aucune URL statique n'est jamais renvoyee au client.
Toute lecture passe par une URL presignee a expiration courte (`services/storage.py`,
`get_presigned_url`), generee a la demande. Les originaux ne sont accessibles que via
`routers/download.py`, apres verification que la commande est payee.

## Pipeline photo

Voir le schema dans [README.md](../README.md#architecture) pour la vue synthetique. Details par
etape :

### 1. Ingestion (`services/ingestion.py`)

Point d'entree unique partage entre l'upload manuel (`routers/photos.py`) et le dossier surveille
(`services/folder_watcher.py`) : validation (type MIME, taille max 25 Mo), generation de la
miniature de grille (400px, qualite 80) et de la preview plein ecran (1600px, qualite 88) via
Pillow, upload des trois variantes (original + 2 derives) vers le stockage, creation de la ligne
`Photo`. **L'original n'est jamais recompresse ni redimensionne** — garantie de non-degradation
demandee explicitement.

### 2. Indexation faciale (`services/face_indexing.py`, `services/face_recognition.py`)

Tache de fond declenchee apres upload (`index_photos_faces`, parallelisme borne — voir
[#parallelisme-de-lindexation](#parallelisme-de-lindexation-ci-dessous)). Pour chaque photo :
telechargement de l'original, decodage OpenCV, detection via InsightFace (`buffalo_l`, GPU si
disponible sinon CPU automatique), un embedding 512-d normalise par visage detecte au-dessus du
seuil de confiance (`FACE_DETECTION_MIN_CONFIDENCE`). Toute erreur marque la photo `FAILED` sans
jamais faire remonter d'exception non geree (la fonction est protegee de bout en bout).

**Concurrence critique** : InsightFace/onnxruntime n'est pas garanti thread-safe pour des appels
concurrents sur la meme session partagee — un verrou global asyncio serialise strictement les
appels d'inference (`_inference_lock` dans `face_recognition.py`). Tout le reste (telechargement
storage, ecritures DB) n'est **pas** derriere ce verrou et peut se chevaucher entre photos.

### Parallelisme de l'indexation

`index_photos_faces` (traitement d'un lot d'upload) utilise un `asyncio.Semaphore` pour traiter
plusieurs photos en parallele (defaut : 4) plutot que de les passer une par une a
`BackgroundTasks.add_task` (qui les executerait strictement sequentiellement, un comportement de
FastAPI facile a manquer). Seule l'inference GPU reste serialisee par `_inference_lock` ; les
telechargements storage et les commits DB de photos differentes se recouvrent. Sur un gros lot
(100+ photos), cela reduit fortement le temps total par rapport a un traitement 100% sequentiel,
dont la latence reseau (stockage distant, base geree) domine le cout par photo.

### 3. Recherche par selfie (`routers/faces.py`)

Un embedding est calcule sur le selfie envoye par le navigateur (camera, capture cote client). La
comparaison se fait par distance cosinus contre les embeddings de l'evenement (index HNSW
pgvector), avec un seuil de similarite (`FACE_MATCH_SIMILARITY_THRESHOLD`). Le selfie n'est jamais
persiste.

### 4. Groupage (`routers/events.py`, `_compute_face_clusters`)

DBSCAN (scikit-learn, `metric="cosine"`) sur tous les embeddings d'un evenement. `eps` est une
**distance** cosinus (donc `1 - similarite`), coherent avec le seuil de scan pour que "meme
personne" signifie la meme chose partout dans l'app. Un point de bruit DBSCAN (aucun voisin a moins
de `eps`) n'est **jamais rejete** : il forme son propre groupe a une photo (identifiants negatifs
synthetiques, distincts des labels DBSCAN reels), pour qu'une personne photographiee une seule fois
reste retrouvable dans la vue "personnes detectees".

Chaque groupe expose une vignette **recadree sur le visage** (`services/face_crops.py`), pas la
photo entiere : crop carre centre sur la bounding box du visage representatif (marge de 60% pour un
cadrage naturel), genere une fois puis mis en cache dans le stockage (cle deterministe par
`face_embedding.id`) — jamais recalcule a chaque affichage.

### 5. Panier, commande, paiement

Panier identifie par `session_id` (pas de compte invite), TTL configurable. Le frontend applique une
mise a jour optimiste (l'UI reagit instantanement) puis serialise les appels reseau via une chaine
de promesses, pour garantir que la premiere requete cree bien la session panier avant que les
suivantes ne la reutilisent, meme en cas de clics rapides.

Paiement : aucun operateur Mobile Money n'a d'API reellement branchee (voir
`services/payments.py`, chaque adaptateur reel leve `NotImplementedError` tant qu'aucune cle n'est
fournie). Le flux **reellement utilise** est un QR code marchand statique par evenement
(`event_payment_methods`) : le client scanne, paie hors-app, declare "j'ai paye"
(`POST /payments/{id}/mark-paid`, statut `AWAITING_CONFIRMATION`), l'organisateur verifie et
confirme manuellement (`POST /admin/orders/{id}/confirm`). A ce moment, une notification push est
envoyee a l'organisateur (voir plus bas) et un SMS de confirmation au client.

### 6. Telechargement

`routers/download.py` : accessible tant que `order.status == SUCCESS`, sans limite de nombre de
visites (les URLs presignees sont regenerees a chaque appel, jamais stockees). Un QR code permanent
pointe toujours vers la meme page de telechargement — utile si le client n'a pas pu finir de
telecharger et revient plus tard.

## Dossier surveille (ingestion automatique)

`services/folder_watcher.py` : boucle de polling (pas d'evenements filesystem type inotify/watchdog
— un bind-mount Docker Desktop sur Windows ne propage pas toujours fiablement ces evenements). Scan
periodique de `WATCHED_FOLDER_PATH/<event_id>/`, un sous-dossier par evenement. Un fichier n'est
ingere que lorsque sa taille est stable entre deux scans consecutifs (evite de lire un fichier
encore en cours de copie). Etat expose via `GET /events/{id}/watched-folder`, affiche en direct dans
l'admin (statut par fichier : copie en cours / ajoutee / erreur).

## Notifications push (PWA admin)

Web Push standard (VAPID), pas de dependance a un service tiers payant type Firebase. Le frontend
admin est une PWA installable (`manifest.json` + `sw.js`) ; l'abonnement (`PushSubscription`) est
stocke cote backend (`push_subscriptions`, une ligne par navigateur/appareil). Declenchement unique
: quand un client passe une commande en `AWAITING_CONFIRMATION` (a valider), toutes les
souscriptions de l'organisateur proprietaire de l'evenement recoivent une notification. Les
abonnements expires (reponse 404/410 du service push) sont nettoyes automatiquement.

## Preservation de la qualite photo

Exigence explicite : une photo ne doit **jamais** etre degradee entre la prise et le telechargement
client. Concretement : `original_key` pointe vers les bytes exacts recus a l'upload, sans
recompression ni redimensionnement a aucune etape ; seuls `thumbnail_key` (400px) et `preview_key`
(1600px) — des derives generes en plus, jamais en remplacement — sont compresses, et uniquement
utilises pour l'affichage galerie/apercu, jamais pour le telechargement post-achat
(`routers/download.py` sert toujours `original_key`).

## Frontend : points d'architecture notables

- **Virtualisation** (`react-window`) pour la galerie : necessaire pour tenir des evenements de
  plusieurs milliers de photos sans degrader les performances de rendu.
- **Chargement progressif** (`components/gallery/PhotoLightbox.tsx`) : la miniature (deja en cache
  depuis la grille) s'affiche instantanement ; la preview (plus grande, plus nette) charge en
  arriere-plan et prend le relais en fondu des qu'elle est prete — jamais de spinner visible.
- **Mise a jour optimiste + file serialisee** (galerie, scan, panier) : l'UI reagit au clic sans
  attendre le reseau, tout en garantissant l'ordre des mutations serveur via une chaine de
  promesses par composant.
- **`React.memo` cible** sur les cellules de la grille photo, avec comparateur explicite, pour
  qu'un re-rendu du composant parent (ex: changement de selection) ne re-rende pas les 500+ cellules
  non concernees.
