from fastapi import FastAPI
from app.core.config import settings
from app.core.database import engine, Base
from app.modules.auth.router import router as auth_router

# Création automatique des tables de la base de données PostgreSQL locales
# (Utile en développement. En production, Alembic est privilégié)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME, 
    version="0.1.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Enregistrement des points d'accès (routes)
app.include_router(auth_router, prefix=settings.API_V1_STR)

@app.get("/")
def read_root():
    return {"message": f"Bienvenue sur l'API de {settings.PROJECT_NAME}"}
