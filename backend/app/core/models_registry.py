"""
Point d'import unique pour tous les modules de modèles SQLAlchemy.

Chaque module métier (auth, comptes, transactions, ...) définit ses propres
modèles, mais tant qu'un module n'a pas encore de router/service qui les
importe, `Base.metadata` ne les connaît pas. Ce fichier centralise ces
imports pour Alembic (autogenerate) et pour les tests (création du schéma
en mémoire), sans dépendre de l'existence des endpoints métier.
"""
from app.modules.auth import models as _auth_models  # noqa: F401
from app.modules.audit import models as _audit_models  # noqa: F401
from app.modules.plans import models as _plans_models  # noqa: F401
from app.modules.comptes import models as _comptes_models  # noqa: F401
from app.modules.budgets import models as _budgets_models  # noqa: F401
from app.modules.transactions import models as _transactions_models  # noqa: F401
from app.modules.epargne import models as _epargne_models  # noqa: F401
from app.modules.dettes import models as _dettes_models  # noqa: F401
from app.modules.rapports import models as _rapports_models  # noqa: F401
from app.modules.jarvis import models as _jarvis_models  # noqa: F401
from app.modules.analyse import models as _analyse_models  # noqa: F401
from app.modules.notifications import models as _notifications_models  # noqa: F401
from app.modules.tontines import models as _tontines_models  # noqa: F401
from app.modules.avis import models as _avis_models  # noqa: F401
