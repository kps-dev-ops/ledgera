"""Tâches Celery pour le rafraîchissement de la vue matérialisée balance_mensuelle.

`refresh_balance_mensuelle(schema)` rafraîchit pour un tenant donné.
`refresh_balance_tous_tenants()` itère tous les tenants (planifié via beat).
"""
from celery import shared_task
from celery.utils.log import get_task_logger
from django.db import connection
from django_tenants.utils import schema_context

logger = get_task_logger(__name__)


@shared_task
def refresh_balance_mensuelle(schema_name: str) -> str:
    """Rafraîchit la vue matérialisée d'un tenant. Utilise CONCURRENTLY si possible
    (exige un index unique, présent par défaut)."""
    with schema_context(schema_name):
        with connection.cursor() as c:
            try:
                c.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY balance_mensuelle")
                logger.info("balance_mensuelle (CONCURRENT) rafraîchie pour %s", schema_name)
            except Exception:
                c.execute("REFRESH MATERIALIZED VIEW balance_mensuelle")
                logger.warning("balance_mensuelle (BLOQUANT) rafraîchie pour %s", schema_name)
    return f"OK: {schema_name}"


@shared_task
def refresh_balance_tous_tenants() -> int:
    """Dispatch refresh_balance_mensuelle pour chaque tenant connu."""
    from apps.tenants.models import Societe

    n = 0
    for schema in Societe.objects.exclude(schema_name="public").values_list(
        "schema_name", flat=True
    ):
        refresh_balance_mensuelle.delay(schema)
        n += 1
    return n
