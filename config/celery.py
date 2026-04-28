import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
app = Celery("ledgera")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "refresh-balance-tous-tenants": {
        "task": "apps.etats.tasks.refresh_balance_tous_tenants",
        "schedule": crontab(hour=3, minute=0),
    },
}
