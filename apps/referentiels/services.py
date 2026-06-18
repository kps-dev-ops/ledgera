import json
from pathlib import Path

from .models import CompteType, PlanComptableType

DATA_DIR = Path(__file__).parent / "data"


def charger_plan_depuis_fichier(nom_fichier: str) -> PlanComptableType:
    """Charge un plan de comptes type depuis un fichier JSON de `data/`. Idempotent.

    Structure : {"plan": {code, libelle, pays_applicable, version},
    "comptes": [{numero, libelle, classe, sens, collectif_tiers, analytique_ok, parent}]}.
    Comptes ordonnés parent avant enfant.
    """
    data = json.loads((DATA_DIR / nom_fichier).read_text(encoding="utf-8"))
    plan, _ = PlanComptableType.objects.get_or_create(
        code=data["plan"]["code"],
        defaults={
            "libelle": data["plan"]["libelle"],
            "pays_applicable": data["plan"]["pays_applicable"],
            "version": data["plan"]["version"],
        },
    )
    instances: dict[str, CompteType] = {}
    racines = [c for c in data["comptes"] if c["parent"] is None]
    enfants = [c for c in data["comptes"] if c["parent"] is not None]
    for c in racines:
        obj, _ = CompteType.objects.get_or_create(
            plan=plan, numero=c["numero"],
            defaults={k: v for k, v in c.items() if k not in ("parent", "numero")},
        )
        instances[c["numero"]] = obj
    for c in enfants:
        parent = instances.get(c["parent"]) or CompteType.objects.filter(plan=plan, numero=c["parent"]).first()
        obj, _ = CompteType.objects.get_or_create(
            plan=plan, numero=c["numero"],
            defaults={**{k: v for k, v in c.items() if k not in ("parent", "numero")}, "parent": parent},
        )
        instances[c["numero"]] = obj
    return plan
