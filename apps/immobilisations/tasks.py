from celery import shared_task
from django_tenants.utils import get_tenant_model, schema_context

from apps.comptabilite.models import Exercice


@shared_task
def comptabiliser_dotations_mensuel(annee: int, mois: int, user_id: int):
    """Pour chaque tenant, comptabilise les dotations PREVUE de (annee, mois).

    `user_id` : utilisateur système portant l'écriture (auteur de la pièce).
    """
    from django.contrib.auth import get_user_model

    from .services import comptabiliser_dotations

    resultats = {}
    for tenant in get_tenant_model().objects.exclude(schema_name="public"):
        with schema_context(tenant.schema_name):
            try:
                exercice = Exercice.objects.get(date_debut__year=annee)
            except Exercice.DoesNotExist:
                continue
            user = get_user_model().objects.filter(pk=user_id).first()
            piece = comptabiliser_dotations(exercice, mois, user)
            resultats[tenant.schema_name] = piece.id if piece else None
    return resultats
