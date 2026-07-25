from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

# Un seul beat scheduler doit tourner à la fois (déploiement Celery Beat
# standard) — c'est ce qui rend inutile un verrou distribué inter-process
# pour verifier_et_executer_recurrences (voir transactions.service).
celery_app = Celery(
    "mynkap",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.worker.tasks"],
)

celery_app.conf.beat_schedule = {
    "verifier-transactions-recurrentes-quotidien": {
        "task": "app.worker.tasks.verifier_transactions_recurrentes",
        # 00h05 chaque jour : après minuit pour éviter toute ambiguïté de
        # fuseau horaire sur "le jour J", avant les heures d'usage typique.
        "schedule": crontab(hour=0, minute=5),
    },
    "generer-snapshots-mensuels": {
        "task": "app.worker.tasks.generer_snapshots_mensuels",
        # Le 1er de chaque mois, après la vérification quotidienne des
        # récurrences du même jour (00h05) pour partir de données à jour.
        "schedule": crontab(day_of_month=1, hour=1, minute=0),
    },
}
celery_app.conf.timezone = "UTC"
