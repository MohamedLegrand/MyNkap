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
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 11520 # 8 jours

    # CORS : origines autorisées à appeler l'API (séparées par des virgules dans .env)
    CORS_ORIGINS: str = "http://localhost:5173"

    # Broker/backend Celery (tâches de fond : transactions récurrentes...)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Fournisseurs IA (module JARVIS, à venir) — optionnelles : rien ne les
    # consomme encore, un clone du dépôt sans ces clés doit rester capable
    # de lancer l'app et les tests.
    GROQ_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
