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


@pytest.mark.django_db
def test_provisionner_sans_domaine():
    call_command("charger_plan_pcg")
    societe = provisionner_societe(
        code="SANS_DOM", schema_name="sans_dom", raison_sociale="Sans domaine SAS",
        pays="FR", devise="EUR", referentiel="PCG", plan_code="PCG_2014",
    )
    assert Domain.objects.filter(tenant=societe, domain="sans_dom.local").exists()


@pytest.mark.django_db
def test_une_societe_provisionnee_est_utilisable_immediatement():
    """Garde contre « il y a une société mais pas de données ».

    Provisionner ne suffisait pas : les configurations fiscales et les catégories
    d'immobilisation manquaient, donc les écrans TVA/IS et le formulaire
    d'immobilisation presentaient des listes vides, sans moyen de les remplir depuis
    l'application.
    """
    call_command("charger_plan_pcg")
    societe = provisionner_societe(
        code="ETW_FR", schema_name="etw_fr", raison_sociale="EasyToWork France SAS",
        pays="FR", devise="EUR", referentiel="PCG", plan_code="PCG_2014",
    )
    from apps.fiscal.models import ConfigurationIS, ConfigurationTVA
    from apps.immobilisations.models import CategorieImmobilisation

    with tenant_context(societe):
        assert ConfigurationTVA.objects.filter(actif=True).exists(), "aucune configuration TVA"
        assert ConfigurationIS.objects.filter(actif=True).exists(), "aucune configuration IS"
        assert CategorieImmobilisation.objects.exists(), "aucune categorie d'immobilisation"
        # Nomenclature francaise, pas SYSCOHADA.
        assert ConfigurationTVA.objects.get().compte_tva_due.numero == "44551"


@pytest.mark.django_db
def test_societe_syscohada_amorcee_avec_categories_et_fiscalite():
    """Pendant SYSCOHADA du test precedent.

    Le plan SYSCOHADA livre s'arretait aux totalisateurs (24, 28, 681, 44) : ni les
    categories d'immobilisation ni les configurations fiscales ne pouvaient etre
    creees, faute des comptes de detail. Ce test verifie le plan ET l'amorcage.
    """
    from apps.referentiels.services import charger_plan_depuis_fichier

    charger_plan_depuis_fichier("syscohada_2017.json")
    societe = provisionner_societe(
        code="KPS_BJ", schema_name="kps_bj", raison_sociale="KPS Bénin SARL",
        pays="BJ", devise="XOF", referentiel="SYSCOHADA", plan_code="SYSCOHADA_2017",
    )
    from apps.fiscal.models import ConfigurationAIB, ConfigurationIS, ConfigurationTVA
    from apps.immobilisations.models import CategorieImmobilisation

    with tenant_context(societe):
        assert CategorieImmobilisation.objects.count() == 4
        mat_info = CategorieImmobilisation.objects.get(code="MAT-INFO")
        assert mat_info.compte_immo.numero == "2442"
        assert mat_info.compte_amortissement.numero == "2844"

        assert ConfigurationTVA.objects.get().compte_tva_due.numero == "4441"
        assert ConfigurationIS.objects.get().compte_charge_impot.numero == "891"
        # L'AIB est propre au Benin : elle doit exister ici, contrairement au PCG.
        assert ConfigurationAIB.objects.get().compte_aib.numero == "4492"
