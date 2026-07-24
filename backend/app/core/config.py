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
    SECRET_KEY: str = "remplacer-par-une-cle-secrete-tres-securisee"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 11520 # 8 jours

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
