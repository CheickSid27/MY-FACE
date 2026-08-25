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
    # Similarite cosinus min pour considerer deux visages comme la meme personne
    # (1.0 = identique). Seuil configurable par evenement dans une phase ulterieure.
    face_match_similarity_threshold: float = 0.45
    # DBSCAN sur les embeddings normalises (voir routers/events.py,
    # _compute_face_clusters) : eps est une DISTANCE cosinus (1 - similarite),
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

    # Panier invite
    cart_session_ttl_hours: int = 24

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

    # SMS (Africa's Talking) — non configure par defaut, voir services/sms.py
    africastalking_username: str = ""
    africastalking_api_key: str = ""
    africastalking_sender_id: str = ""

    # Notifications push (PWA admin) — voir services/push_notifications.py.
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
    # docker-compose.yml) — affiche a l'organisateur pour qu'il sache ou
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
