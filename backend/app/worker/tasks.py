from app.core.database import SessionLocal
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
