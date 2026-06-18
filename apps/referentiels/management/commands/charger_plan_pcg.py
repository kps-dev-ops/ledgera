from django.core.management.base import BaseCommand

from apps.referentiels.models import CompteType
from apps.referentiels.services import charger_plan_depuis_fichier


class Command(BaseCommand):
    help = "Charge le plan de comptes PCG français (2014) dans les référentiels (idempotent)"

    def handle(self, *args, **options):
        plan = charger_plan_depuis_fichier("pcg_2014.json")
        total = CompteType.objects.filter(plan=plan).count()
        self.stdout.write(self.style.SUCCESS(f"Plan PCG chargé — {total} comptes."))
