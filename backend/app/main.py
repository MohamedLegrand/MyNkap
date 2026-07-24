from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.exceptions import MyNkapException
from app.core.limiter import limiter
from app.core import models_registry  # noqa: F401 (enregistre toutes les tables/relations)
from app.modules.auth.router import router as auth_router
from app.modules.comptes.router import router as comptes_router
from app.modules.transactions.router import router as transactions_router
from app.modules.dettes.router import router as dettes_router

# Le schéma de la base de données est géré par Alembic (voir backend/alembic/).
# Lancer `alembic upgrade head` avant de démarrer l'API.

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(MyNkapException)
def mynkap_exception_handler(_request: Request, exc: MyNkapException):
    return JSONResponse(status_code=400, content={"detail": str(exc) or "Erreur applicative MyNkap."})

# Enregistrement des points d'accès (routes)
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(comptes_router, prefix=settings.API_V1_STR)
app.include_router(transactions_router, prefix=settings.API_V1_STR)
app.include_router(dettes_router, prefix=settings.API_V1_STR)

@app.get("/")
def read_root():
    return {"message": f"Bienvenue sur l'API de {settings.PROJECT_NAME}"}
