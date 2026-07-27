from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "MyNkap Backend"
    API_V1_STR: str = "/api/v1"

    # Base de données
    DATABASE_URL: str = "postgresql://postgres:123@localhost:5432/mynkap"

    @property
    def sync_database_url(self) -> str:
        # Gère les cas où les bases de données (comme Supabase/Render) utilisent le protocole postgres://
        if self.DATABASE_URL.startswith("postgres://"):
            return self.DATABASE_URL.replace("postgres://", "postgresql://", 1)
        return self.DATABASE_URL

    # Sécurité
    # Pas de valeur par défaut : doit être fournie via .env (voir .env.example).
    # Génération : python -c "import secrets; print(secrets.token_urlsafe(64))"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS : origines autorisées à appeler l'API (séparées par des virgules dans .env)
    CORS_ORIGINS: str = "http://localhost:5173"

    # Broker/backend Celery (tâches de fond : transactions récurrentes...)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Fournisseurs IA (module JARVIS, à venir) — optionnelles : rien ne les
    # consomme encore, un clone du dépôt sans ces clés doit rester capable
    # de lancer l'app et les tests.
    GROQ_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None

    # Paiement Mobile Money (module Plans/Abonnement) — optionnelles, même
    # raison que ci-dessus.
    HRPAY_PUBLIC_KEY: str | None = None
    HRPAY_SECRET_KEY: str | None = None

    # Envoi d'e-mails transactionnels (mot de passe oublié...) via l'API
    # REST Brevo — optionnelle, même raison que ci-dessus (sans clé, on
    # retombe sur une simulation console, cf. auth.services).
    BREVO_API_KEY: str | None = None
    MAIL_FROM_EMAIL: str = "no-reply@mynkap.com"
    MAIL_FROM_NAME: str = "MyNkap"

    # Base du frontend, utilisée pour construire les liens envoyés par e-mail
    # (ex: /reset-password?token=...).
    FRONTEND_URL: str = "http://localhost:5173"

    # Dossier de stockage des rapports PDF générés (module Rapports).
    # Chemin local pour l'instant — un stockage cloud (S3/Supabase) sera
    # nécessaire en production, sans changer l'API du module.
    RAPPORTS_DOSSIER: str = "rapports_generes"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
