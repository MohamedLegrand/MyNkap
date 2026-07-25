from app.core.database import SessionLocal
from app.modules.analyse.service import generer_snapshots_mensuels_tous_clients
from app.modules.transactions.service import verifier_et_executer_recurrences
from app.worker.celery_app import celery_app


@celery_app.task(name="app.worker.tasks.verifier_transactions_recurrentes")
def verifier_transactions_recurrentes() -> int:
    """
    Tâche planifiée quotidiennement (voir celery_app.beat_schedule). Simple
    enveloppe : toute la logique vit dans transactions.service pour rester
    testable sans Celery/Redis démarrés — voir tests/test_transactions.py.
    """
    db = SessionLocal()
    try:
        resultats = verifier_et_executer_recurrences(db)
        return len(resultats)
    finally:
        db.close()


@celery_app.task(name="app.worker.tasks.generer_snapshots_mensuels")
def generer_snapshots_mensuels() -> int:
    """
    Tâche planifiée le 1er de chaque mois (voir celery_app.beat_schedule).
    Fige un snapshot AnalyseFinanciere + Prediction du mois précédent pour
    chaque client — voir analyse.service pour le détail.
    """
    db = SessionLocal()
    try:
        return generer_snapshots_mensuels_tous_clients(db)
    finally:
        db.close()
