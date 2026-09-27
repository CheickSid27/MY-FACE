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
| `photos` | Une photo uploadee : cles de stockage (original/thumbnail/preview/preview filigranee), statut d'indexation |
| `face_embeddings` | Un embedding 512-d (pgvector) par visage detecte, + bounding box, nettete, cle de vignette (`crop_key`) |
| `cart_sessions` / `cart_items` | Panier invite, identifie par un `session_id` (pas de compte requis), TTL, tirage papier par photo |
| `orders` / `order_items` | Commande (telephone E.164) + snapshot des photos achetees, prix unitaire et tirage au moment de l'achat |
| `event_payment_methods` | QR marchand + numero, par evenement et par moyen de paiement |
| `push_subscriptions` | Abonnements Web Push d'un organisateur (PWA), un par navigateur/appareil installe |

Suppressions en cascade au niveau base (`ON DELETE CASCADE`, relations ORM en `passive_deletes`
pour ne pas tout charger en memoire) : supprimer un evenement supprime ses photos, qui suppriment
leurs embeddings ; supprimer une photo non vendue supprime ses lignes de panier/commande associees.
Une photo deja presente dans une commande **payee** (`SUCCESS`) ne peut pas etre supprimee, et un
evenement ayant au moins une commande payee non plus (409, `routers/photos.py` et
`routers/events.py`) : l'acces post-achat d'un client ne doit jamais casser. Apres suppression,
tous les fichiers de l'element sont retires du stockage (prefixe `events/{id}/` pour un evenement).

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
miniature de grille (400px, qualite 80), de la preview plein ecran (1600px, qualite 88) et de sa
copie filigranee (`services/watermark.py`) via Pillow, calculs executes dans un thread, puis
upload des quatre variantes en parallele, creation de la ligne `Photo`. **L'original n'est jamais
recompresse ni redimensionne**, garantie de non-degradation demandee explicitement.

**Orientation EXIF** : un telephone enregistre souvent les pixels "couches" + un tag Orientation.
Les derives sont generes apres `ImageOps.exif_transpose` (`thumbnails.open_oriented`), comme le
fait OpenCV cote detection : miniatures droites et vignettes-visages recadrees au bon endroit.

### 2. Indexation faciale (`services/face_indexing.py`, `services/face_recognition.py`)

Tache de fond declenchee apres upload (`index_photos_faces`, parallelisme borne, voir
[#parallelisme-de-lindexation](#parallelisme-de-lindexation-ci-dessous)). Pour chaque photo :
telechargement de l'original, decodage OpenCV, detection via InsightFace (`buffalo_l`, GPU si
disponible sinon CPU automatique), un embedding 512-d normalise par visage detecte au-dessus du
seuil de confiance (`FACE_DETECTION_MIN_CONFIDENCE`) et assez net (`FACE_MIN_SHARPNESS`). Toute
erreur marque la photo `FAILED` sans jamais faire remonter d'exception non geree (la fonction est
protegee de bout en bout).

**Idempotence et reprise** : re-indexer une photo remplace ses embeddings (jamais de doublon). Les
taches d'indexation vivent dans le process (pas de file de messages) : un redemarrage les perd.
Au demarrage, `recover_unfinished_indexing` reprend toute photo restee `pending`/`processing`
(5 photos etaient restees bloquees des semaines avant ce mecanisme). L'admin voit l'etat par
photo et peut relancer les echecs (`POST /events/{id}/reindex`). Un registre en memoire evite de
programmer deux fois la meme photo.

**Concurrence critique** : InsightFace/onnxruntime n'est pas garanti thread-safe pour des appels
concurrents sur la meme session partagee, un verrou global asyncio serialise strictement les
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

### 4. Groupage (`services/face_clusters.py`)

DBSCAN (scikit-learn, `metric="cosine"`, execute dans un thread) sur tous les embeddings d'un
evenement. `eps` est une **distance** cosinus (donc `1 - similarite`), coherent avec le seuil de
scan pour que "meme personne" signifie la meme chose partout dans l'app. Un point de bruit DBSCAN
(aucun voisin a moins de `eps`) n'est **jamais rejete** : il forme son propre groupe a une photo
(identifiants negatifs synthetiques, distincts des labels DBSCAN reels), pour qu'une personne
photographiee une seule fois reste retrouvable dans la vue "personnes detectees".

Chaque groupe expose une vignette **recadree sur le visage** (`services/face_crops.py`), pas la
photo entiere : crop carre centre sur la bounding box du visage representatif (marge de 60% pour un
cadrage naturel), genere une fois ; sa cle est memorisee sur l'embedding (`crop_key`), sans plus
jamais interroger le stockage pour savoir s'il existe.

**Cache** (`FaceClusterCache`) : le calcul complet (rapatriement des vecteurs depuis Neon, DBSCAN,
vignettes) prenait 11 a 60 s a CHAQUE ouverture de "Trouver mon visage", avec des 504. Le resultat
est desormais memorise par evenement et invalide a chaque indexation/suppression de photo :
- l'admin recoit toujours un resultat a jour (recalcul si perime) ;
- les invites recoivent immediatement le dernier resultat pendant qu'un recalcul tourne en
  arriere-plan (une photo tout juste indexee apparait quelques secondes plus tard) ;
- un seul calcul a la fois par evenement, les requetes simultanees attendent le meme resultat ;
- les evenements recents sont pre-calcules au demarrage du backend.
Les URLs signees ne sont jamais mises en cache (regenerees a chaque reponse, calcul local).
Mesure : 0,5 s par ouverture (latence reseau comprise), contre 11-60 s auparavant.

### Stockage : appels non bloquants (`services/storage.py`)

boto3 est synchrone. Appele directement dans une fonction `async`, chaque aller-retour R2 bloquait
toute la boucle d'evenements (mesure : `/health` passait de 9 ms a 8,8 s pendant un calcul de
groupes, pour tous les utilisateurs). Tous les appels reseau (upload, download, head, delete,
suppression par prefixe) passent par `asyncio.to_thread` ; seule la signature d'URL (calcul local)
reste directe. Meme principe pour les calculs Pillow/DBSCAN et la lecture des fichiers du dossier
surveille.

### 5. Panier, commande, paiement

Panier identifie par `session_id` (pas de compte invite), TTL configurable. Le frontend applique une
mise a jour optimiste (l'UI reagit instantanement) puis serialise les appels reseau via une chaine
de promesses, pour garantir que la premiere requete cree bien la session panier avant que les
suivantes ne la reutilisent, meme en cas de clics rapides.

Paiement : aucun operateur Mobile Money n'a d'API reellement branchee (voir
`services/payments.py`, chaque adaptateur reel leve `NotImplementedError` tant qu'aucune cle n'est
fournie). Le flux **reellement utilise** est un QR code marchand statique par evenement
(`event_payment_methods`) : le client scanne, paie hors-app, declare "j'ai paye"
(`POST /payments/{id}/mark-paid`, statut `AWAITING_CONFIRMATION`), une notification push part vers
l'organisateur, qui verifie et confirme manuellement (`POST /admin/orders/{id}/confirm`) ; le SMS
de confirmation part alors vers le client (`services/orders.set_order_status`, point unique de
changement de statut). A la borne, le paiement en especes cree directement une commande a
confirmer.

`/payments/init` exige un moyen de paiement reel : l'ancien repli (sans moyen choisi → adaptateur
"manual") creait des commandes `processing` que ni le client ni l'organisateur ne pouvaient
debloquer (3 en production). Le panier n'a plus aucun repli : si les moyens de paiement ne se
chargent pas, il affiche une erreur avec "Reessayer".

**Cycle de vie** (`services/orders.py`) : une commande `pending` jamais payee passe `cancelled`
apres `ORDER_PENDING_TTL_MINUTES` (60 par defaut). Pas de minuteur (il empecherait Neon de se
mettre en veille) : l'expiration est appliquee au demarrage et a la lecture (statut consulte par
le client, liste/statistiques organisateur). Une commande `awaiting_confirmation` n'expire jamais
(de l'argent a peut-etre ete envoye). L'organisateur peut annuler une commande jamais payee, ou
valider une commande expiree/rejetee si le paiement est finalement arrive. Les paniers expires
depuis plus de 7 jours sont purges au demarrage.

**Telephone** (`services/phone.py`) : indicatif pays choisi par le client (Cote d'Ivoire par
defaut), numero national verifie selon le format reel du pays (longueur, prefixes mobiles), stocke
en E.164 (`+2250701020304`, format attendu par Africa's Talking). La meme table est exposee au
frontend (`GET /meta/phone-countries`) : validation identique pendant la saisie.

### 6. Telechargement

`routers/download.py` : accessible tant que `order.status == SUCCESS`, sans limite de nombre de
visites (les URLs presignees sont regenerees a chaque appel, jamais stockees ; la page les
renouvelle avant expiration si elle reste ouverte). Chaque photo a son lien de telechargement
(original, `Content-Disposition: attachment` sous son nom d'origine) et s'affiche en miniature
(afficher les originaux faisait telecharger des dizaines de Mo au telephone rien que pour la
liste). Le zip est genere et envoye photo par photo (`StreamingResponse`, une seule photo en
memoire), nginx le transmet sans tampon. Un QR code permanent pointe toujours vers la meme page de
telechargement, utile si le client n'a pas pu finir de telecharger et revient plus tard.

## Tirages papier (systeme d'impression)

Le tirage papier se commande **uniquement a la borne** (une imprimante n'existe que sur place) :
1. Panier de la borne : case "+ Imprimer" par photo, si l'evenement a un prix d'impression. Cocher
   exige le `kiosk_token` de l'evenement, verifie serveur (`PATCH /cart/{item_id}`), pas seulement
   masque cote frontend. Prix fige dans la commande (`order_items.print_price`).
2. Paiement (QR ou especes a la borne), puis validation par l'organisateur.
3. La page de telechargement de la borne affiche "Imprimer mes photos" → `/order/{id}/print` :
   originaux en pleine qualite, attendus entierement avant d'autoriser l'impression, une photo par
   page dans son orientation (pages CSS nommees portrait/paysage), sans recadrage (`contain`).
   `window.print()` ; avec Chrome lance en `--kiosk-printing`, impression directe sur
   l'imprimante par defaut, sans boite de dialogue.
4. Une fois imprime, `POST /download/{id}/printed` renseigne `orders.printed_at` (autorise a la
   borne via son jeton, ou a l'organisateur connecte). La page previent si c'est deja imprime.
5. Filet de securite : l'admin (page Paiements) liste les **tirages a imprimer** (commandes payees
   avec tirages et sans `printed_at`) et peut les imprimer depuis un poste relie a l'imprimante ;
   la fiche commande a aussi un bouton "Imprimer les tirages".

## Fiche commande / recu

`GET /admin/orders/{id}` renvoie tout ce qu'il faut pour repondre a un client qui revient avec un
probleme : evenement, date, telephone, moyen et reference de paiement, liste nominative des photos
(nom de fichier, prix, tirage), detail du montant (photos au prix unitaire + tirages - lots/remises
= total), date d'impression, lien permanent de telechargement. Affichee dans l'historique des
paiements (recherche par telephone, numero de commande ou reference) et imprimable en A4
(`/admin/orders/{id}/receipt`, avec le QR de telechargement du client).

## Filigrane et mode borne

L'apercu 1600px est assez net pour etre capture et utilise sans achat. Chaque photo a donc une
copie filigranee (`preview_watermarked_key`, motif "MYFACE" diagonal repete, semi-transparent,
`services/watermark.py`), seule version grand format servie au **telephone d'un invite**. L'apercu
net est reserve a :
- la **borne** : endpoints publics appeles avec le `kiosk_token` de l'evenement, verifie serveur
  (`services/access.is_kiosk_request`, comparaison a temps constant) ;
- l'**organisateur** (endpoints authentifies).
Photo sans version filigranee (rattrapage au demarrage en cours) : le telephone recoit la
miniature, jamais l'apercu net (`services/photo_urls.py`).

Le jeton borne conditionne aussi, **cote serveur**, les deux usages physiques : paiement en
especes (`/payments/init`, 403 sans jeton valide) et tirage papier (`PATCH /cart/{item_id}`).

Le frontend memorise le **jeton** borne en `sessionStorage` (`lib/kiosk.ts`), pas un simple
drapeau : l'accueil le re-verifie a chaque retour (reset d'inactivite compris). Avant, le reset
renvoyait vers l'accueil sans `?kiosk=` et la borne perdait son mode (especes, impression, reset)
des le premier client. Le jeton est retire de la barre d'adresse une fois memorise.

## Dossier surveille (ingestion automatique)

`services/folder_watcher.py` : boucle de polling (pas d'evenements filesystem type inotify/watchdog
un bind-mount Docker Desktop sur Windows ne propage pas toujours fiablement ces evenements). Scan
periodique de `WATCHED_FOLDER_PATH/<event_id>/`, un sous-dossier par evenement (cree
automatiquement a la creation de l'evenement). Un fichier n'est ingere que lorsque sa taille est
stable entre deux scans consecutifs (evite de lire un fichier encore en cours de copie). Etat
expose via `GET /events/{id}/watched-folder`, affiche en direct dans l'admin (statut par fichier :
copie en cours / ajoutee / erreur).

Le scan ne touche **que le disque** : la base n'est interrogee que lorsqu'un fichier nouveau ou
modifie est pret. Auparavant, chaque scan (toutes les 5 s, en permanence) listait les evenements
en base, ce qui empechait Neon de se mettre en veille et consommait son quota gratuit. Un fichier
en erreur n'est retente que s'il est remplace ; un fichier deja present en base (redemarrage) est
reconnu par son nom sans etre relu.

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
(1600px), des derives generes en plus, jamais en remplacement, sont compresses, et uniquement
utilises pour l'affichage galerie/apercu, jamais pour le telechargement post-achat
(`routers/download.py` sert toujours `original_key`).

## Frontend : points d'architecture notables

- **Virtualisation** (`react-window`) pour la galerie : necessaire pour tenir des evenements de
  plusieurs milliers de photos sans degrader les performances de rendu.
- **Chargement progressif** (`components/gallery/PhotoLightbox.tsx`) : la miniature (deja en cache
  depuis la grille) s'affiche instantanement ; la preview (plus grande, plus nette) charge en
  arriere-plan et prend le relais en fondu des qu'elle est prete, jamais de spinner visible.
- **Mise a jour optimiste + file serialisee** (galerie, scan, panier) : l'UI reagit au clic sans
  attendre le reseau, tout en garantissant l'ordre des mutations serveur via une chaine de
  promesses par composant.
- **`React.memo` cible** sur les cellules de la grille photo, avec comparateur explicite, pour
  qu'un re-rendu du composant parent (ex: changement de selection) ne re-rende pas les 500+ cellules
  non concernees.
- **Dialogues imbriques** (scan, "Trouver mon visage") : la visionneuse ouverte depuis un dialogue
  arrete la propagation de ses clics, sinon fermer une photo fermait aussi tout le dialogue.
- **Resynchronisation du panier** : le dialogue de scan previent la galerie apres chaque
  modification ; la galerie relit le panier serveur en conservant les ajouts encore en attente
  d'envoi (pas de "flicker" de selection).

## Demarrage du backend

Au lancement (`app/main.py`, en arriere-plan, sans retarder l'API) : migrations Alembic et compte
admin (commande du conteneur), prechargement du modele InsightFace (GPU), demarrage du dossier
surveille, puis rattrapages : expiration des commandes jamais payees et purge des vieux paniers,
reprise des indexations interrompues, filigrane des photos qui n'en ont pas, pre-calcul des groupes
de visages des evenements recents. Les logs applicatifs (`myface.*`) apparaissent dans
`docker logs`.
