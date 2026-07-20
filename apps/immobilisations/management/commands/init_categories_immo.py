from django.core.management.base import BaseCommand, CommandError
from django_tenants.utils import tenant_context

from apps.immobilisations.services import init_categories_immo_par_defaut
from apps.tenants.models import Societe


class Command(BaseCommand):
    help = "Crée les catégories d'immobilisation par défaut dans un schema tenant."

    def add_arguments(self, parser):
        parser.add_argument("schema", help="Nom du schema tenant (ex. kps_bj)")

    def handle(self, *args, **options):
        # On passe par la Societe, et non par `schema_context`, parce que les catégories
        # dépendent du référentiel comptable : les numéros de comptes SYSCOHADA et PCG
        # n'ont rien en commun sur les immobilisations.
        societe = Societe.objects.filter(schema_name=options["schema"]).first()
        if societe is None:
            connus = ", ".join(
                Societe.objects.exclude(schema_name="public").values_list("schema_name", flat=True)
            )
            raise CommandError(f"Schema '{options['schema']}' introuvable. Connus : {connus or '(aucun)'}")

        with tenant_context(societe):
            n = init_categories_immo_par_defaut(societe)
        self.stdout.write(
            self.style.SUCCESS(f"{n} catégorie(s) créée(s) — référentiel {societe.referentiel}.")
        )
