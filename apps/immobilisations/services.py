import calendar
from datetime import date
from decimal import Decimal

from django.db import transaction

from apps.comptabilite.models import Journal, LigneEcriture, PieceComptable
from apps.comptabilite.services import valider_piece

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
            immobilisation=immo, annee=ligne.annee, mois=ligne.mois,
            montant=ligne.montant, cumul=ligne.cumul, vnc=ligne.vnc, statut="PREVUE",
        )
        for ligne in lignes
        if (ligne.annee, ligne.mois) not in deja
    ]
    Dotation.objects.bulk_create(objets)
    if immo.statut == "EN_COURS":
        immo.statut = "EN_SERVICE"
        immo.save(update_fields=["statut"])
    return objets


def _fin_de_mois(annee: int, mois: int) -> date:
    return date(annee, mois, calendar.monthrange(annee, mois)[1])


@transaction.atomic
def comptabiliser_dotations(exercice, mois: int, user) -> PieceComptable | None:
    """Génère une pièce OD consolidée pour (exercice, mois) à partir des dotations
    PREVUE de l'année de l'exercice. Retourne None si rien à comptabiliser.
    """
    annee = exercice.date_debut.year
    dotations = list(
        Dotation.objects.select_for_update()
        .filter(annee=annee, mois=mois, statut="PREVUE")
        .select_related("immobilisation")
    )
    if not dotations:
        return None

    journal_od = Journal.objects.get(code="OD")
    piece = PieceComptable.objects.create(
        journal=journal_od, exercice=exercice, date_piece=_fin_de_mois(annee, mois),
        reference=f"DOT-{annee}-{mois:02d}",
        libelle=f"Dotations aux amortissements {mois:02d}/{annee}",
        statut="BROUILLARD", auteur=user,
    )
    numero_ligne = 1
    for d in dotations:
        immo = d.immobilisation
        LigneEcriture.objects.create(
            piece=piece, numero_ligne=numero_ligne, compte=immo.compte_dotation,
            libelle=f"Dotation {immo.code}", debit=d.montant, credit=Decimal("0.00"),
        )
        LigneEcriture.objects.create(
            piece=piece, numero_ligne=numero_ligne + 1, compte=immo.compte_amortissement,
            libelle=f"Amortissement {immo.code}", debit=Decimal("0.00"), credit=d.montant,
        )
        numero_ligne += 2

    valider_piece(piece, user)
    Dotation.objects.filter(pk__in=[d.pk for d in dotations]).update(
        statut="COMPTABILISEE", piece_generee=piece
    )
    return piece
