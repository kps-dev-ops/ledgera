from django.db import IntegrityError
from django.test import TestCase

from apps.referentiels.models import CompteType, PlanComptableType


class TestPlanComptableType(TestCase):
    def setUp(self):
        self.plan = PlanComptableType.objects.create(
            code="SYSCOHADA_2017",
            libelle="Système Comptable OHADA — Révisé 2017",
            pays_applicable="OHADA",
            version="2017",
        )

    def test_creation_plan(self):
        assert str(self.plan) == "SYSCOHADA_2017 — Système Comptable OHADA — Révisé 2017"

    def test_code_unique(self):
        with self.assertRaises(IntegrityError):
            PlanComptableType.objects.create(
                code="SYSCOHADA_2017",
                libelle="Doublon",
                pays_applicable="OHADA",
                version="2017",
            )

    def test_ordering_par_code(self):
        PlanComptableType.objects.create(
            code="PCG_FR_2025", libelle="PCG France", pays_applicable="FR", version="2025"
        )
        plans = list(PlanComptableType.objects.values_list("code", flat=True))
        assert plans == sorted(plans)


class TestCompteType(TestCase):
    def setUp(self):
        self.plan = PlanComptableType.objects.create(
            code="SYSCOHADA_2017", libelle="SYSCOHADA", pays_applicable="OHADA", version="2017"
        )

    def test_creation_compte(self):
        compte = CompteType.objects.create(
            plan=self.plan,
            numero="401",
            libelle="Fournisseurs, dettes en compte",
            classe=4,
            sens="crediteur",
            collectif_tiers=True,
            analytique_ok=False,
        )
        assert compte.numero == "401"
        assert compte.collectif_tiers is True
        assert str(compte) == "401 — Fournisseurs, dettes en compte"

    def test_numero_unique_par_plan(self):
        CompteType.objects.create(
            plan=self.plan, numero="401", libelle="Premier", classe=4, sens="crediteur"
        )
        with self.assertRaises(IntegrityError):
            CompteType.objects.create(
                plan=self.plan, numero="401", libelle="Doublon", classe=4, sens="crediteur"
            )

    def test_meme_numero_dans_plans_differents(self):
        plan2 = PlanComptableType.objects.create(
            code="PCG_FR_2025", libelle="PCG France", pays_applicable="FR", version="2025"
        )
        CompteType.objects.create(
            plan=self.plan, numero="401", libelle="SYSCOHADA 401", classe=4, sens="crediteur"
        )
        CompteType.objects.create(
            plan=plan2, numero="401", libelle="PCG 401", classe=4, sens="crediteur"
        )
        assert CompteType.objects.filter(numero="401").count() == 2

    def test_arborescence_parent_enfant(self):
        parent = CompteType.objects.create(
            plan=self.plan, numero="40", libelle="Fournisseurs", classe=4, sens="crediteur"
        )
        enfant = CompteType.objects.create(
            plan=self.plan,
            numero="401",
            libelle="Fournisseurs dettes",
            classe=4,
            sens="crediteur",
            parent=parent,
        )
        assert enfant.parent == parent
        assert parent.enfants.count() == 1

    def test_ordering_par_numero(self):
        CompteType.objects.create(
            plan=self.plan, numero="701", libelle="Ventes", classe=7, sens="crediteur"
        )
        CompteType.objects.create(
            plan=self.plan, numero="401", libelle="Fournisseurs", classe=4, sens="crediteur"
        )
        numeros = list(
            CompteType.objects.filter(plan=self.plan).values_list("numero", flat=True)
        )
        assert numeros == sorted(numeros)


class TestChargerPlanSyscohada(TestCase):
    def test_commande_charge_les_comptes(self):
        from django.core.management import call_command

        call_command("charger_plan_syscohada", verbosity=0)
        assert PlanComptableType.objects.filter(code="SYSCOHADA_2017").exists()
        assert CompteType.objects.filter(plan__code="SYSCOHADA_2017").count() > 20

    def test_commande_idempotente(self):
        from django.core.management import call_command

        call_command("charger_plan_syscohada", verbosity=0)
        count1 = CompteType.objects.filter(plan__code="SYSCOHADA_2017").count()
        call_command("charger_plan_syscohada", verbosity=0)
        count2 = CompteType.objects.filter(plan__code="SYSCOHADA_2017").count()
        assert count1 == count2
