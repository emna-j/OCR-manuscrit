"""Configuration centralisée de l'application.

Les valeurs proviennent des variables d'environnement puis du fichier
`.env` situé à la racine du projet (jamais committé, voir .gitignore).
Aucun secret n'est défini en dur dans ce module.
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Racine du projet (3 niveaux au-dessus de ce fichier : core -> app -> backend -> racine)
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Secure Manuscript Intelligence Platform"
    app_version: str = "0.1.0"
    environment: str = "development"

    # Origines CORS autorisées, séparées par des virgules.
    cors_origins: str = "http://localhost:5173"

    # Connexion PostgreSQL (psycopg 3).
    database_url: str = "postgresql+psycopg://manuscript:change_me@localhost:5432/manuscript_ai"

    # ---- Gemini VLM ----
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"
    # ---- Gemini VLM ----
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"
    # Modèles de secours (séparés par des virgules) : les quotas free tier sont
    # PAR MODÈLE. Si le quota journalier du modèle principal est épuisé (429),
    # ou si un modèle n'est plus disponible pour la clé (404), l'appel bascule
    # automatiquement sur le suivant → l'analyse continue de fonctionner au
    # lieu de renvoyer une erreur 502 à l'utilisateur.
    gemini_fallback_models: str = "gemini-3.7-flash,gemini-3.8-flash"
    # Budget de "réflexion" (thinking) envoyé au modèle :
    #   0   = thinking désactivé → réponses nettement plus rapides (recommandé) ;
    #   N>0 = budget de tokens de réflexion ;
    #   -1  = ne pas envoyer ThinkingConfig (comportement par défaut du modèle,
    #         plus lent sur les modèles "thinking").
    gemini_thinking_budget: int = 0

    # ---- Stockage des fichiers ----
    storage_backend: str = "local"  # "local" | "minio"
    storage_local_dir: str = "data/uploads"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = ""
    minio_secret_key: str = ""
    minio_bucket_documents: str = "documents"
    minio_secure: bool = False

    # ---- Authentification (JWT) ----
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # ---- Seuils de confiance (Human-in-the-loop) ----
    # Valeurs provisoires — à calibrer sur le dataset d'évaluation (Phase 14).
    ocr_confidence_threshold: float = 0.75
    analysis_confidence_threshold: float = 0.70

    # ---- Détection PII ----
    # Complément NER Gemini pour PERSON/ADDRESS/ORGANIZATION/LOCATION.
    # Désactivable pour économiser le quota Gemini (1 appel de moins par analyse).
    # Les types structurés (EMAIL, PHONE, DATE_OF_BIRTH, ID_NUMBER) sont
    # toujours détectés par regex, indépendamment de ce réglage.
    pii_use_gemini: bool = True

    # ---- Upload ----
    max_upload_size_mb: int = 10
    allowed_extensions: str = "png,jpg,jpeg,pdf"
    max_pdf_pages: int = 10
    max_image_dimension: int = 8000

    # ---- Rate limiting ----
    rate_limit_max_requests: int = 60
    rate_limit_window_seconds: int = 60

    # ---- Compte administrateur initial (créé par python -m app.seed) ----
    admin_email: str = ""
    admin_password: str = ""
    admin_full_name: str = "Administrator"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def allowed_extension_list(self) -> list[str]:
        return [ext.strip().lower() for ext in self.allowed_extensions.split(",") if ext.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()