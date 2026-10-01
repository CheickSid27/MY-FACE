from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"

    secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    database_url: str
    # Base dediee aux tests automatises : toujours un Postgres local jetable,
    # jamais Neon/production (latence reseau + on ne veut jamais que la suite
    # de tests touche une base geree a distance). Si vide, tests/conftest.py
    # retombe sur l'ancien comportement (derive de database_url).
    test_database_url: str = ""

    storage_backend: str = "local"

    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_storage_bucket: str = "myface-photos"

    s3_endpoint_url: str = "http://minio:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "myface-photos"
    s3_region: str = "us-east-1"
    s3_public_url: str = "http://localhost:9000"

    cors_origins: str = "http://localhost:3000"

    initial_admin_email: str = "admin@myface-events.com"
    initial_admin_password: str = "changeme"

    # Reconnaissance faciale (InsightFace / buffalo_l)
    face_recognition_providers: str = "CUDAExecutionProvider,CPUExecutionProvider"
    face_detection_min_confidence: float = 0.5
    # Variance du Laplacien sur le crop du visage (voir face_recognition.py) :
    # rejette les visages trop flous (photos en mode portrait/bokeh, mouvement)
    # AVANT de creer leur embedding, meme si InsightFace les detecte avec une
    # confidence elevee (le det_score mesure "y a-t-il un visage ici", pas sa
    # nettete). Calibre empiriquement sur les photos reelles d'un evenement :
    # les visages nettement flous scoraient sous ~40, la masse des visages
    # normaux commence vers 43+. 30 reste volontairement conservateur pour
    # ne pas rejeter a tort un vrai visage juste moyennement net.
    face_min_sharpness: float = 30.0
    # Similarite cosinus min pour considerer deux visages comme la meme personne
    # (1.0 = identique). Seuil configurable par evenement dans une phase ulterieure.
    face_match_similarity_threshold: float = 0.45
    # DBSCAN sur les embeddings normalises (voir services/face_clusters.py,
    # compute_event_clusters) : eps est une DISTANCE cosinus (1 - similarite),
    # pas une distance euclidienne. On reutilise le meme seuil de similarite
    # que le scan visiteur pour que "meme personne" veuille dire la meme chose
    # partout dans l'app. BUG CORRIGE : l'ancienne version utilisait
    # metric="euclidean" avec eps=0.4, ce qui exigeait une similarite cosinus
    # >= 0.92 pour regrouper deux visages (quasi jamais atteint en pratique,
    # d'ou des groupes vides malgre des visages correctement detectes).
    # = 1 - face_match_similarity_threshold (garde en dur pour eviter toute
    # ambiguite d'ordre d'evaluation dans le corps de classe Pydantic).
    face_cluster_eps: float = 0.55
    face_cluster_min_samples: int = 2
    # Duree de vie max du cache memoire des groupes de visages (voir
    # services/face_clusters.py). Le cache est de toute facon invalide des
    # qu'une photo de l'evenement est indexee/supprimee : ce delai n'est
    # qu'un filet de securite (ex: modification faite directement en base).
    face_cluster_cache_ttl_seconds: int = 600
    # Neon met sa base en veille apres ~5 min sans activite et ferme alors les
    # connexions : le premier visiteur tombait sur « connection is closed ».
    # - les connexions de plus de N secondes sont remplacees avant usage ;
    # - une requete minimale toutes les N secondes garde la base eveillee tant
    #   que l'application tourne (0 = desactive). Pas de pool_pre_ping : il
    #   ajouterait un aller-retour de ~190 ms a CHAQUE requete.
    db_pool_recycle_seconds: int = 240
    db_keepalive_seconds: int = 240

    # Panier invite
    cart_session_ttl_hours: int = 24

    # Commande jamais payee (QR jamais scanne, client parti...) : annulee
    # automatiquement passe ce delai (voir services/orders.py) au lieu de
    # rester "en attente" indefiniment. Ne s'applique JAMAIS a une commande
    # "awaiting_confirmation" (le client declare avoir paye : seul
    # l'organisateur tranche).
    order_pending_ttl_minutes: int = 60

    # Paiement (Phase 3). PAYMENT_PROVIDER=manual = adaptateur de secours SANS
    # aucun mouvement d'argent reel (voir services/payments.py), utilise tant
    # qu'aucune cle marchand Wave/Orange/MTN/Moov n'est fournie.
    payment_provider: str = "manual"
    payment_webhook_secret: str = "changeme-webhook-secret"
    download_url_ttl_seconds: int = 900

    wave_api_key: str = ""
    orange_money_api_key: str = ""
    orange_money_merchant_id: str = ""
    mtn_money_api_key: str = ""
    mtn_money_subscription_key: str = ""
    moov_money_api_key: str = ""

    # --- GeniusPay (passerelle tierce, en test sandbox, voir
    # services/geniuspay.py et routers/geniuspay.py) : chemin de paiement
    # ISOLE du flux QR marchand + confirmation manuelle deja en place
    # (services/payments.py, event_payment_methods). Ne remplace rien tant
    # que non valide ; les deux coexistent. ---
    geniuspay_api_key: str = ""
    geniuspay_api_secret: str = ""
    geniuspay_webhook_secret: str = ""
    geniuspay_base_url: str = "https://geniuspay.ci/api/v1/merchant"

    # SMS (Africa's Talking), non configure par defaut, voir services/sms.py
    africastalking_username: str = ""
    africastalking_api_key: str = ""
    africastalking_sender_id: str = ""

    # Notifications push (PWA admin), voir services/push_notifications.py.
    # Si vide, l'envoi est simplement ignore (pas d'erreur), meme logique que
    # sms.py quand aucun credential n'est configure.
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = ""

    # Utilise pour construire les liens de telechargement/QR renvoyes a l'invite
    app_base_url: str = "http://localhost:3000"

    # Dossier surveille (ingestion automatique) : chemin CONTENEUR (monte
    # depuis un dossier reel du PC hote via docker-compose.yml) contenant un
    # sous-dossier par evenement (watched_folder_path/<event_id>/). Tout
    # fichier image qui y apparait (ex: copie depuis une carte SD d'appareil
    # photo) est ingere automatiquement, voir services/folder_watcher.py.
    watched_folder_path: str = "/watched"
    watched_folder_poll_seconds: float = 5.0
    # Chemin cote PC hote correspondant (purement informatif : le conteneur ne
    # voit jamais ce chemin, seulement /watched via le bind-mount de
    # docker-compose.yml), affiche a l'organisateur pour qu'il sache ou
    # deposer les photos depuis la carte SD de l'appareil.
    watched_folder_host_display_path: str = "watched-photos"

    @property
    def face_recognition_providers_list(self) -> list[str]:
        return [p.strip() for p in self.face_recognition_providers.split(",") if p.strip()]

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
