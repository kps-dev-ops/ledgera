import json
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.referentiels.models import CompteType, PlanComptableType


class Command(BaseCommand):
    help = "Charge le plan de comptes SYSCOHADA 2017 dans les référentiels (idempotent)"

    def handle(self, *args, **options):
        data_path = Path(__file__).parent.parent.parent / "data" / "syscohada_2017.json"
        data = json.loads(data_path.read_text(encoding="utf-8"))

        plan, created = PlanComptableType.objects.get_or_create(
            code=data["plan"]["code"],
            defaults={
                "libelle": data["plan"]["libelle"],
                "pays_applicable": data["plan"]["pays_applicable"],
                "version": data["plan"]["version"],
            },
        )
        action = "Créé" if created else "Existant"
        self.stdout.write(f"{action} : {plan}")

        comptes_data = data["comptes"]
        numero_vers_instance: dict[str, CompteType] = {}

        comptes_racine = [c for c in comptes_data if c["parent"] is None]
        comptes_enfants = [c for c in comptes_data if c["parent"] is not None]

        for c in comptes_racine:
            obj, _ = CompteType.objects.get_or_create(
                plan=plan,
                numero=c["numero"],
                defaults={k: v for k, v in c.items() if k not in ("parent", "numero")},
            )
            numero_vers_instance[c["numero"]] = obj

        for c in comptes_enfants:
            parent = numero_vers_instance.get(c["parent"])
            obj, _ = CompteType.objects.get_or_create(
                plan=plan,
                numero=c["numero"],
                defaults={
                    **{k: v for k, v in c.items() if k not in ("parent", "numero")},
                    "parent": parent,
                },
            )
            numero_vers_instance[c["numero"]] = obj

        total = CompteType.objects.filter(plan=plan).count()
        self.stdout.write(self.style.SUCCESS(f"Plan SYSCOHADA chargé — {total} comptes."))
