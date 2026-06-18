from .models import DeclarationTVA


def declarations_is_par_exercice(exercice) -> list:
    from .models import DeclarationIS

    return list(DeclarationIS.objects.filter(exercice=exercice).select_related("configuration"))


def declarations_par_annee(annee: int) -> list:
    return list(DeclarationTVA.objects.filter(annee=annee).select_related("configuration"))


def obligations_tva(config, annee: int) -> list[dict]:
    """Liste des périodes attendues (selon périodicité) avec statut déclaré/à faire."""
    nb = 12 if config.periodicite == "MENSUELLE" else 4
    declarees = set(
        DeclarationTVA.objects.filter(configuration=config, annee=annee).values_list("periode_num", flat=True)
    )
    return [{"periode_num": p, "declaree": p in declarees} for p in range(1, nb + 1)]
