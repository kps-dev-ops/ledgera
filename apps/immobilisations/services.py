from django.db import transaction

from .amortissement import plan_degressif, plan_lineaire
from .models import Dotation, Immobilisation


@transaction.atomic
def next_code_immobilisation() -> str:
    """Prochain code immo séquentiel, format IMM######."""
    last = (
        Immobilisation.objects.select_for_update()
        .filter(code__startswith="IMM")
        .order_by("-code")
        .first()
    )
    n = int(last.code[3:]) + 1 if last else 1
    return f"IMM{n:06d}"


@transaction.atomic
def generer_plan_amortissement(immo: Immobilisation) -> list[Dotation]:
    """Calcule et persiste les Dotation PREVUE de l'immo. Idempotent : ne régénère
    que si aucune dotation PREVUE n'existe (ne touche jamais une COMPTABILISEE).
    Passe l'immo EN_SERVICE.
    """
    if immo.dotations.filter(statut="PREVUE").exists():
        return list(immo.dotations.filter(statut="PREVUE"))

    calc = plan_lineaire if immo.mode_amortissement == "LINEAIRE" else plan_degressif
    lignes = calc(immo.cout_acquisition, immo.valeur_residuelle, immo.duree, immo.date_mise_service)

    deja = set(immo.dotations.values_list("annee", "mois"))
    objets = [
        Dotation(
            immobilisation=immo, annee=l.annee, mois=l.mois,
            montant=l.montant, cumul=l.cumul, vnc=l.vnc, statut="PREVUE",
        )
        for l in lignes
        if (l.annee, l.mois) not in deja
    ]
    Dotation.objects.bulk_create(objets)
    if immo.statut == "EN_COURS":
        immo.statut = "EN_SERVICE"
        immo.save(update_fields=["statut"])
    return objets
