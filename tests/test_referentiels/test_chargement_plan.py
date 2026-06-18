from django.core.management import call_command
from django.test import TestCase

from apps.referentiels.models import CompteType, PlanComptableType


class TestChargementPCG(TestCase):
    def test_charge_plan_pcg(self):
        call_command("charger_plan_pcg")
        plan = PlanComptableType.objects.get(code="PCG_2014")
        assert plan.pays_applicable == "FR"
        comptes = CompteType.objects.filter(plan=plan)
        assert comptes.count() == 65
        c44566 = comptes.get(numero="44566")
        assert c44566.parent.numero == "445"
        assert comptes.get(numero="401").collectif_tiers is True

    def test_idempotent(self):
        call_command("charger_plan_pcg")
        call_command("charger_plan_pcg")
        assert CompteType.objects.filter(plan__code="PCG_2014").count() == 65


class TestChargementSyscohadaInchange(TestCase):
    def test_syscohada_charge_toujours(self):
        call_command("charger_plan_syscohada")
        assert PlanComptableType.objects.filter(code="SYSCOHADA_2017").exists()
        assert CompteType.objects.filter(plan__code="SYSCOHADA_2017").count() > 0
