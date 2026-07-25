import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.core.database import Base, get_db
from app.core import models_registry  # noqa: F401 (enregistre toutes les tables)
from app.main import app, limiter
from app.modules.plans.models import Plan

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Même catalogue que le seed de la migration Alembic (voir
# 0513c3e2bc26_restructurer_plan...) — nécessaire ici aussi car la base de
# test SQLite est recréée à vide pour chaque test, sans passer par les
# migrations. Toute inscription échouerait sans ça (creer_abonnement_gratuit
# a besoin d'un plan GRATUIT existant).
PLANS_SEED = [
    {"nom": "GRATUIT", "prix_mensuel": 0, "prix_annuel": 0, "devise": "XAF",
     "acces_dettes": False, "acces_epargne": False, "acces_recurrentes": False,
     "acces_templates": False, "acces_analyse": False, "acces_jarvis": False, "acces_rapport": False},
    {"nom": "ESSENTIEL", "prix_mensuel": 1000, "prix_annuel": 10000, "devise": "XAF",
     "acces_dettes": True, "acces_epargne": True, "acces_recurrentes": True,
     "acces_templates": True, "acces_analyse": False, "acces_jarvis": False, "acces_rapport": False},
    {"nom": "PREMIUM", "prix_mensuel": 2500, "prix_annuel": 25000, "devise": "XAF",
     "acces_dettes": True, "acces_epargne": True, "acces_recurrentes": True,
     "acces_templates": True, "acces_analyse": True, "acces_jarvis": True, "acces_rapport": False},
]


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    session.add_all(Plan(**donnees) for donnees in PLANS_SEED)
    session.commit()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    limiter.reset()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
