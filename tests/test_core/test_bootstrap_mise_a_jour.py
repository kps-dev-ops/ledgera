"""Re-executer `bootstrap_tenant` doit RATTRAPER une société déjà provisionnée.

C'est le cas réel d'une préproduction : la société existe, créée avant que le plan de
comptes ne soit complété et avant que l'amorçage fiscal n'existe. La commande doit
combler ce qui manque, pas se contenter de constater que la société est là.
"""

import pytest
from django.core.management import call_command
from django_tenants.utils import tenant_context

from apps.comptabilite.models import CompteComptable
from apps.fiscal.models import ConfigurationAIB, ConfigurationIS, ConfigurationTVA
from apps.immobilisations.models import CategorieImmobilisation
from apps.referentiels.models import CompteType
from apps.tenants.models import Societe

# Comptes ajoutés au plan APRÈS la première mise en service : une installation
# existante ne les a pas.
AJOUTS_RECENTS = ["4441", "4449", "441", "891", "4492", "2442", "2844", "6813"]


@pytest.mark.django_db
def test_reexecution_rattrape_une_societe_incomplete():
    call_command("bootstrap_tenant")
    societe = Societe.objects.get(code="KPS_BJ")

    # On ramène l'installation à son état d'avant : plan tronqué, aucune configuration
    # fiscale, aucune catégorie d'immobilisation.
    CompteType.objects.filter(numero__in=AJOUTS_RECENTS).delete()
    with tenant_context(societe):
        # Les configurations d'abord : elles référencent les comptes en PROTECT.
        ConfigurationTVA.objects.all().delete()
        ConfigurationIS.objects.all().delete()
        ConfigurationAIB.objects.all().delete()
        CategorieImmobilisation.objects.all().delete()
        CompteComptable.objects.filter(numero__in=AJOUTS_RECENTS).delete()

    call_command("bootstrap_tenant")

    # Le plan partagé doit avoir été rechargé — c'était le point de blocage : la
    # commande sautait le chargement dès que le plan existait, même périmé.
    assert CompteType.objects.filter(numero__in=AJOUTS_RECENTS).count() == len(AJOUTS_RECENTS)

    with tenant_context(societe):
        # …puis recopié dans le schema de la société…
        assert CompteComptable.objects.filter(numero__in=AJOUTS_RECENTS).count() == len(AJOUTS_RECENTS)
        # …ce qui rend enfin l'amorçage fiscal et les catégories possibles.
        assert ConfigurationTVA.objects.get().compte_tva_due.numero == "4441"
        assert ConfigurationIS.objects.get().compte_charge_impot.numero == "891"
        assert CategorieImmobilisation.objects.count() == 4


@pytest.mark.django_db
def test_reexecution_ne_duplique_rien():
    call_command("bootstrap_tenant")
    call_command("bootstrap_tenant")

    societe = Societe.objects.get(code="KPS_BJ")
    assert Societe.objects.filter(code="KPS_BJ").count() == 1
    with tenant_context(societe):
        assert ConfigurationTVA.objects.count() == 1
        assert ConfigurationIS.objects.count() == 1
        assert CategorieImmobilisation.objects.count() == 4
        assert CompteComptable.objects.filter(numero="4441").count() == 1
