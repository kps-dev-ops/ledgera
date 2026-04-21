from django.core.management.base import BaseCommand
from django.core.management import call_command
from apps.tenants.models import Societe, Domain
from apps.referentiels.models import PlanComptableType


class Command(BaseCommand):
    help = "Crée un tenant initial KPS Bénin avec le plan de comptes SYSCOHADA"

    def handle(self, *args, **options):
        if not PlanComptableType.objects.filter(code="SYSCOHADA_2017").exists():
            call_command("charger_plan_syscohada")

        plan = PlanComptableType.objects.get(code="SYSCOHADA_2017")

        if Societe.objects.filter(code="KPS_BJ").exists():
            self.stdout.write("Tenant KPS_BJ existe déjà.")
            return

        societe = Societe.objects.create(
            schema_name="kps_bj",
            code="KPS_BJ",
            raison_sociale="KPS Bénin SARL",
            pays="BJ",
            devise="XOF",
            referentiel="SYSCOHADA",
            plan_comptes_type=plan,
        )

        Domain.objects.create(
            domain="kps-benin.localhost",
            tenant=societe,
            is_primary=True,
        )

        self.stdout.write(self.style.SUCCESS(
            f"Tenant créé : {societe} — schema: {societe.schema_name}"
        ))
        self.stdout.write("Domaine : kps-benin.localhost")
