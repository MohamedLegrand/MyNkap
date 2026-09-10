"""
Tests unitaires de l'authentification : hachage/vérification de mot de
passe et jeton JWT (backend/app/core/security.py), ainsi que la remise à
zéro du compteur d'échecs de connexion (auth.services). Aucun accès base
de données, aucun client HTTP — tout est calculé en mémoire ou sur un objet
construit directement en Python.
"""
from datetime import datetime, timedelta

from jose import jwt

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.modules.auth.models import Utilisateur
from app.modules.auth.services import _reinitialiser_tentatives_echouees


# --- Mot de passe (bcrypt) ---

def test_verify_password_reconnait_le_bon_mot_de_passe():
    hache = get_password_hash("motdepasse123")
    assert verify_password("motdepasse123", hache) is True


def test_verify_password_rejette_un_mauvais_mot_de_passe():
    hache = get_password_hash("motdepasse123")
    assert verify_password("autremotdepasse", hache) is False


def test_deux_hachages_du_meme_mot_de_passe_sont_differents():
    # bcrypt inclut un sel aléatoire à chaque appel : deux hachages du même
    # mot de passe ne doivent jamais être identiques (sinon deux comptes
    # avec le même mot de passe seraient reconnaissables en base).
    assert get_password_hash("motdepasse123") != get_password_hash("motdepasse123")


# --- Jeton JWT ---

def test_create_access_token_contient_le_bon_sujet():
    token = create_access_token(subject="42")
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload["sub"] == "42"


def test_create_access_token_expiration_par_defaut_dans_le_futur():
    token = create_access_token(subject="42")
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert datetime.utcfromtimestamp(payload["exp"]) > datetime.utcnow()


def test_create_access_token_respecte_lexpiration_personnalisee():
    token = create_access_token(subject="42", expires_delta=timedelta(minutes=5))
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    expiration = datetime.utcfromtimestamp(payload["exp"])
    # Doit expirer dans ~5 minutes, pas dans les ACCESS_TOKEN_EXPIRE_MINUTES par défaut.
    assert timedelta(minutes=4) < expiration - datetime.utcnow() <= timedelta(minutes=5)


def test_create_access_token_rejete_avec_une_mauvaise_cle():
    token = create_access_token(subject="42")
    try:
        jwt.decode(token, "une-mauvaise-cle-secrete", algorithms=[settings.ALGORITHM])
        assert False, "le décodage aurait dû échouer"
    except jwt.JWTError:
        pass


# --- Compteur d'échecs de connexion ---

def test_reinitialiser_tentatives_echouees_remet_tout_a_zero():
    utilisateur = Utilisateur(
        type="client",
        tentatives_echouees=4,
        alerte_tentatives_envoyee=True,
        verrouille_jusqua=datetime.utcnow() + timedelta(minutes=10),
    )
    _reinitialiser_tentatives_echouees(utilisateur)
    assert utilisateur.tentatives_echouees == 0
    assert utilisateur.alerte_tentatives_envoyee is False
    assert utilisateur.verrouille_jusqua is None
