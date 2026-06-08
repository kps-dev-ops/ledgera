import calendar
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from apps.comptabilite.models import CompteComptable, Journal, LigneEcriture, PieceComptable
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


COMPTE_VALEUR_COMPTABLE_CESSION = "654000"
COMPTE_PRODUIT_CESSION = "754000"
COMPTE_CREANCE_CESSION = "485000"


def _cumul_comptabilise(immo) -> Decimal:
    agg = immo.dotations.filter(statut="COMPTABILISEE").aggregate(s=Sum("montant"))
    return agg["s"] or Decimal("0.00")


def _exercice_de(d):
    from apps.comptabilite.models import Exercice

    return Exercice.objects.get(date_debut__lte=d, date_fin__gte=d)


@transaction.atomic
def ceder_immobilisation(immo, date_cession, prix_cession: Decimal, user) -> PieceComptable:
    """Génère la pièce de cession SYSCOHADA et passe l'immo CEDEE.

    VNC = coût - cumul des amortissements comptabilisés. Sortie de l'actif :
    - débit  28x (cumul)            : solde de l'amortissement
    - débit  654 (VNC)              : valeur comptable cédée
    - crédit 2x  (coût)             : sortie du bien
    - débit  485 (prix)             : créance sur cession
    - crédit 754 (prix)             : produit de cession
    La plus/moins-value = 754 - 654.
    """
    if immo.statut in ("CEDEE", "REBUT"):
        raise ValueError(f"Immobilisation déjà sortie (statut {immo.statut})")

    cumul = _cumul_comptabilise(immo)
    vnc = immo.cout_acquisition - cumul
    journal_od = Journal.objects.get(code="OD")
    c654 = CompteComptable.objects.get(numero=COMPTE_VALEUR_COMPTABLE_CESSION)
    c754 = CompteComptable.objects.get(numero=COMPTE_PRODUIT_CESSION)
    c485 = CompteComptable.objects.get(numero=COMPTE_CREANCE_CESSION)

    derniere = immo.dotations.filter(
        statut="COMPTABILISEE", piece_generee__isnull=False
    ).first()
    exercice = derniere.piece_generee.exercice if derniere else _exercice_de(date_cession)

    piece = PieceComptable.objects.create(
        journal=journal_od, exercice=exercice, date_piece=date_cession,
        reference=f"CES-{immo.code}", libelle=f"Cession {immo.code} — {immo.designation}",
        statut="BROUILLARD", auteur=user,
    )
    lignes = []
    n = 1
    if cumul > 0:
        lignes.append((n, immo.compte_amortissement, cumul, Decimal("0.00")))
        n += 1
    if vnc > 0:
        lignes.append((n, c654, vnc, Decimal("0.00")))
        n += 1
    lignes.append((n, immo.compte_immo, Decimal("0.00"), immo.cout_acquisition))
    n += 1
    if prix_cession > 0:
        lignes.append((n, c485, prix_cession, Decimal("0.00")))
        n += 1
        lignes.append((n, c754, Decimal("0.00"), prix_cession))
        n += 1
    for numero_ligne, compte, debit, credit in lignes:
        LigneEcriture.objects.create(
            piece=piece, numero_ligne=numero_ligne, compte=compte,
            libelle=f"Cession {immo.code}", debit=debit, credit=credit,
        )
    valider_piece(piece, user)

    immo.statut = "CEDEE"
    immo.date_cession = date_cession
    immo.prix_cession = prix_cession
    immo.piece_cession = piece
    immo.save(update_fields=["statut", "date_cession", "prix_cession", "piece_cession"])
    immo.dotations.filter(statut="PREVUE").delete()
    return piece


@transaction.atomic
def mettre_au_rebut(immo, date_rebut, user) -> PieceComptable:
    """Mise au rebut = cession à valeur nulle."""
    piece = ceder_immobilisation(immo, date_rebut, Decimal("0.00"), user)
    immo.statut = "REBUT"
    immo.save(update_fields=["statut"])
    return piece


CATEGORIES_DEFAUT = [
    # (code, libellé, n° compte immo, n° amort, n° dotation, durée, mode)
    ("MAT-INFO", "Matériel informatique", "244400", "284440", "681300", 3, "DEGRESSIF"),
    ("MAT-BUR", "Matériel de bureau", "244100", "284410", "681300", 5, "LINEAIRE"),
    ("MOBILIER", "Mobilier", "244300", "284430", "681300", 10, "LINEAIRE"),
    ("MAT-TRANS", "Matériel de transport", "245000", "284500", "681300", 5, "DEGRESSIF"),
]


@transaction.atomic
def init_categories_immo_par_defaut() -> int:
    """Crée les catégories d'immobilisation standard. Idempotent.
    Les comptes doivent exister dans le plan du tenant (sinon catégorie ignorée).
    """
    from .models import CategorieImmobilisation

    crees = 0
    for code, libelle, n_immo, n_amort, n_dot, duree, mode in CATEGORIES_DEFAUT:
        comptes = {
            c.numero: c
            for c in CompteComptable.objects.filter(numero__in=[n_immo, n_amort, n_dot])
        }
        if not all(n in comptes for n in (n_immo, n_amort, n_dot)):
            continue
        _, created = CategorieImmobilisation.objects.get_or_create(
            code=code,
            defaults={
                "libelle": libelle, "compte_immo": comptes[n_immo],
                "compte_amortissement": comptes[n_amort], "compte_dotation": comptes[n_dot],
                "duree_defaut": duree, "mode_defaut": mode,
            },
        )
        if created:
            crees += 1
    return crees
