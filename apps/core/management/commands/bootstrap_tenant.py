from django.core.management import call_command
from django.core.management.base import BaseCommand
from django_tenants.utils import tenant_context

from apps.referentiels.models import PlanComptableType
from apps.tenants.models import Domain, Societe


class Command(BaseCommand):
    help = "Crée (ou complète) le tenant KPS Bénin avec plan SYSCOHADA, journaux et exercice 2026"

    def handle(self, *args, **options):
        # 1) Plan de comptes type partagé
        if not PlanComptableType.objects.filter(code="SYSCOHADA_2017").exists():
            self.stdout.write("Chargement du plan SYSCOHADA…")
            call_command("charger_plan_syscohada")
        plan = PlanComptableType.objects.get(code="SYSCOHADA_2017")

        # 2) Société (création si absente)
        societe = Societe.objects.filter(code="KPS_BJ").first()
        if societe is None:
            societe = Societe.objects.create(
                schema_name="kps_bj",
                code="KPS_BJ",
                raison_sociale="KPS Bénin SARL",
                pays="BJ",
                devise="XOF",
                referentiel="SYSCOHADA",
                plan_comptes_type=plan,
            )
            Domain.objects.create(domain="kps-benin.localhost", tenant=societe, is_primary=True)
            self.stdout.write(self.style.SUCCESS(f"Tenant créé : {societe}"))
        else:
            self.stdout.write("Tenant KPS_BJ existe déjà — complétion en cours…")
            if not societe.plan_comptes_type_id:
                societe.plan_comptes_type = plan
                societe.save(update_fields=["plan_comptes_type"])

        # 3) Initialisation du contenu tenant (idempotent)
        from apps.comptabilite.services import (
            init_exercice_courant,
            init_journaux_par_defaut,
            init_plan_comptable_pour_societe,
        )
        from apps.fiscal.amorcage import init_configurations_fiscales
        from apps.immobilisations.services import init_categories_immo_par_defaut

        with tenant_context(societe):
            n_comptes = init_plan_comptable_pour_societe(societe)
            # Les journaux d'abord : les configurations fiscales s'y rattachent (journal OD).
            n_journaux = init_journaux_par_defaut()
            exercice = init_exercice_courant(2026)
            n_categories = init_categories_immo_par_defaut(societe)
            rapport_fiscal = init_configurations_fiscales(societe)

        self.stdout.write(self.style.SUCCESS(
            f"  • Plan comptes : {n_comptes} nouveaux comptes ajoutés"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"  • Journaux : {n_journaux} nouveaux journaux ajoutés"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"  • Exercice : {exercice.code} (12 périodes)"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"  • Catégories d'immobilisation : {n_categories} ajoutées"
        ))
        for module, message in rapport_fiscal.items():
            self.stdout.write(self.style.SUCCESS(f"  • Configuration {module} : {message}"))
        self.stdout.write("Domaine : kps-benin.localhost")
