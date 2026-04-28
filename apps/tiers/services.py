from django.db import transaction

from .models import Tiers

PREFIX_PAR_TYPE = {"CLIENT": "C", "FOURNISSEUR": "F", "DIVERS": "D"}


@transaction.atomic
def next_code_auxiliaire(type_tiers: str) -> str:
    """Retourne le prochain code auxiliaire disponible pour un type donné.

    Format : <prefix><6 chiffres>, ex C000001, F000042.
    Le verrou de transaction limite la course ; en cas d'IntegrityError lors du
    save, l'appelant doit retenter (course bénigne en V1).
    """
    if type_tiers not in PREFIX_PAR_TYPE:
        raise ValueError(f"type_tiers inconnu : {type_tiers}")
    prefix = PREFIX_PAR_TYPE[type_tiers]
    last = (
        Tiers.objects.select_for_update()
        .filter(type_tiers=type_tiers, code_auxiliaire__startswith=prefix)
        .order_by("-code_auxiliaire")
        .first()
    )
    n = int(last.code_auxiliaire[1:]) + 1 if last else 1
    return f"{prefix}{n:06d}"
