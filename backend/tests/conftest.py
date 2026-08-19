import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.core.database import Base, get_db
from app.core import models_registry  # noqa: F401 (enregistre toutes les tables)
from app.main import app, limiter
from app.modules.plans.models import Plan, PrixPlanDevise

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
     "acces_templates": False, "acces_analyse": False, "acces_jarvis": False, "acces_rapport": False,
     "acces_tontine": False},
    {"nom": "ESSENTIEL", "prix_mensuel": 1000, "prix_annuel": 10000, "devise": "XAF",
     "acces_dettes": True, "acces_epargne": True, "acces_recurrentes": True,
     "acces_templates": True, "acces_analyse": False, "acces_jarvis": False, "acces_rapport": False,
     "acces_tontine": True},
    {"nom": "PREMIUM", "prix_mensuel": 2500, "prix_annuel": 25000, "devise": "XAF",
     "acces_dettes": True, "acces_epargne": True, "acces_recurrentes": True,
     "acces_templates": True, "acces_analyse": True, "acces_jarvis": True, "acces_rapport": False,
     "acces_tontine": True},
]

# Même catalogue que le seed de la migration Alembic (voir
# 6d751150a5a7_ajouter_prix_plan_devise...) — CDF/GNF/GMD sont des
# estimations, voir le commentaire dans la migration.
PRIX_DEVISE_SEED = {
    "ESSENTIEL": {
        "XAF": (1000, 10000), "XOF": (1000, 10000),
        "CDF": (4700, 47000), "GNF": (14400, 144000), "GMD": (120, 1200),
    },
    "PREMIUM": {
        "XAF": (2500, 25000), "XOF": (2500, 25000),
        "CDF": (11800, 118000), "GNF": (36000, 360000), "GMD": (290, 2900),
    },
}


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    session.add_all(Plan(**donnees) for donnees in PLANS_SEED)
    session.commit()
    for nom_plan, prix_devises in PRIX_DEVISE_SEED.items():
        plan = session.query(Plan).filter(Plan.nom == nom_plan).first()
        session.add_all(
            PrixPlanDevise(id_plan=plan.id_plan, devise=devise, prix_mensuel=mensuel, prix_annuel=annuel)
            for devise, (mensuel, annuel) in prix_devises.items()
        )
    session.commit()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _ne_jamais_envoyer_de_vrais_emails(monkeypatch):
    """
    BREVO_API_KEY est une vraie clé live dans .env (chargée par app.core.config
    au démarrage) — sans ce mock, CHAQUE connexion déclenchée par un test
    (désormais toutes protégées par OTP par e-mail) enverrait un vrai e-mail
    via Brevo. Autouse : aucun test n'a besoin d'y penser explicitement.
    """
    from app.modules.auth import services
    monkeypatch.setattr(services, "_envoyer_email_brevo", lambda *a, **k: None)


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


def se_connecter(client, email: str, mot_de_passe: str):
    """
    Connecte un utilisateur via /auth/login (e-mail + mot de passe, plus de
    double authentification par OTP à cette étape — réservée à la
    vérification de l'e-mail à l'inscription, voir auth.services.verifier_otp)
    et renvoie directement la réponse (access_token, refresh_token,
    user_type...).
    """
    return client.post(
        "/api/v1/auth/login", json={"email": email, "mot_de_passe": mot_de_passe}
    )
