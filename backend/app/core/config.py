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
    # 5175 est le port fixe du frontend MyNkap, voir frontend/vite.config.ts.
    CORS_ORIGINS: str = "http://localhost:5175"

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
    FRONTEND_URL: str = "http://localhost:5175"

    # OAuth Google (Se connecter avec Google) — optionnelles, même raison
    # que les autres clés fournisseur ci-dessus. GOOGLE_CLIENT_SECRET n'est
    # pas utilisé par la vérification du jeton d'identité (audience seule
    # via GOOGLE_CLIENT_ID, voir auth.services._verifier_id_token_google) ;
    # conservé pour un futur flux d'échange de code côté serveur.
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None

    # Dossier de stockage des rapports PDF générés (module Rapports).
    # Chemin local pour l'instant — un stockage cloud (S3/Supabase) sera
    # nécessaire en production, sans changer l'API du module.
    RAPPORTS_DOSSIER: str = "rapports_generes"

    # Dossier de stockage des photos de profil (module Auth/Profile) — même
    # limitation que RAPPORTS_DOSSIER ci-dessus (stockage local, cloud à
    # prévoir en production). Servi via StaticFiles, voir main.py.
    AVATARS_DOSSIER: str = "avatars_uploads"

    # Base publique du backend, utilisée pour construire l'URL absolue des
    # photos de profil hébergées localement (même principe que FRONTEND_URL
    # pour les liens envoyés par e-mail).
    BACKEND_URL: str = "http://localhost:8000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
