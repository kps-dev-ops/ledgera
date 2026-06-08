from django.core.management.base import BaseCommand
from django_tenants.utils import schema_context

from apps.immobilisations.services import init_categories_immo_par_defaut


class Command(BaseCommand):
    help = "Crée les catégories d'immobilisation par défaut dans un schema tenant."

    def add_arguments(self, parser):
        parser.add_argument("schema", help="Nom du schema tenant (ex. kps_bj)")

    def handle(self, *args, **options):
        with schema_context(options["schema"]):
            n = init_categories_immo_par_defaut()
        self.stdout.write(self.style.SUCCESS(f"{n} catégorie(s) créée(s)."))
