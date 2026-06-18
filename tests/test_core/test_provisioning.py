import pytest
from django.core.management import call_command
from django_tenants.utils import tenant_context

from apps.core.services import provisionner_societe
from apps.tenants.models import Domain, Societe


@pytest.mark.django_db
def test_provisionner_societe_france():
    call_command("charger_plan_pcg")
    societe = provisionner_societe(
        code="ETW_FR", schema_name="etw_fr", raison_sociale="EasyToWork France SAS",
        pays="FR", devise="EUR", referentiel="PCG", plan_code="PCG_2014",
        domaine="etw-fr.localhost", annee_exercice=2026,
    )
    assert Societe.objects.filter(code="ETW_FR").exists()
    assert Domain.objects.filter(domain="etw-fr.localhost", tenant=societe).exists()
    from apps.comptabilite.models import CompteComptable, Exercice, Journal
    with tenant_context(societe):
        assert CompteComptable.objects.count() > 0
        assert Journal.objects.filter(code="OD").exists()
        assert Exercice.objects.filter(code="2026").exists()


@pytest.mark.django_db
def test_provisionner_societe_idempotent():
    call_command("charger_plan_pcg")
    kwargs = dict(
        code="ETW_FR", schema_name="etw_fr", raison_sociale="EasyToWork France SAS",
        pays="FR", devise="EUR", referentiel="PCG", plan_code="PCG_2014",
        domaine="etw-fr.localhost",
    )
    provisionner_societe(**kwargs)
    provisionner_societe(**kwargs)
    assert Societe.objects.filter(code="ETW_FR").count() == 1


@pytest.mark.django_db
def test_provisionner_plan_inexistant():
    with pytest.raises(ValueError):
        provisionner_societe(
            code="X", schema_name="x", raison_sociale="X", pays="FR", devise="EUR",
            referentiel="PCG", plan_code="PLAN_INEXISTANT", domaine="x.localhost",
        )
