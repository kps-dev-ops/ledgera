from django.core.management.base import BaseCommand

from apps.core.services import provisionner_societe


class Command(BaseCommand):
    help = "Provisionne une société (schema, plan, journaux, exercice) sans modifier le code."

    def add_arguments(self, parser):
        parser.add_argument("--code", required=True)
        parser.add_argument("--schema", required=True)
        parser.add_argument("--nom", required=True)
        parser.add_argument("--pays", required=True)
        parser.add_argument("--devise", required=True)
        parser.add_argument("--referentiel", required=True)
        parser.add_argument("--plan", required=True, help="Code du PlanComptableType (ex. PCG_2014)")
        parser.add_argument("--domaine", required=True)
        parser.add_argument("--annee", type=int, default=2026)

    def handle(self, *args, **o):
        societe = provisionner_societe(
            code=o["code"], schema_name=o["schema"], raison_sociale=o["nom"], pays=o["pays"],
            devise=o["devise"], referentiel=o["referentiel"], plan_code=o["plan"],
            domaine=o["domaine"], annee_exercice=o["annee"],
        )
        self.stdout.write(self.style.SUCCESS(f"Société provisionnée : {societe} — domaine {o['domaine']}"))
