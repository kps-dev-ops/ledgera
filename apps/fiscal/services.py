import calendar
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Sum

from apps.comptabilite.models import Exercice, LigneEcriture, PieceComptable
from apps.comptabilite.services import valider_piece

from .models import DeclarationAIB, DeclarationIS, DeclarationTVA, RetraitementFiscal


def _bornes_periode(periodicite: str, annee: int, periode_num: int) -> tuple[date, date]:
    if periodicite == "TRIMESTRIELLE":
        mois_debut = (periode_num - 1) * 3 + 1
        mois_fin = mois_debut + 2
    else:
        mois_debut = mois_fin = periode_num
    debut = date(annee, mois_debut, 1)
    fin = date(annee, mois_fin, calendar.monthrange(annee, mois_fin)[1])
    return debut, fin


def _solde(comptes, date_debut, date_fin, sens: str) -> Decimal:
    from apps.comptabilite.models import LigneEcriture

    agg = LigneEcriture.objects.filter(
        compte__in=comptes, piece__statut="VALIDEE",
        piece__date_piece__gte=date_debut, piece__date_piece__lte=date_fin,
    ).aggregate(d=Sum("debit"), c=Sum("credit"))
    d = agg["d"] or Decimal("0.00")
    c = agg["c"] or Decimal("0.00")
    return (c - d) if sens == "CREDITEUR" else (d - c)


def calculer_tva(config, date_debut, date_fin) -> dict:
    """TVA collectée (créditeur) − déductible (débiteur) sur la période."""
    collectee = _solde(config.comptes_collectee.all(), date_debut, date_fin, "CREDITEUR")
    deductible = _solde(config.comptes_deductible.all(), date_debut, date_fin, "DEBITEUR")
    return {"tva_collectee": collectee, "tva_deductible": deductible, "tva_nette": collectee - deductible}


@transaction.atomic
def creer_declaration_tva(config, annee: int, periode_num: int, user) -> DeclarationTVA:
    debut, fin = _bornes_periode(config.periodicite, annee, periode_num)
    res = calculer_tva(config, debut, fin)
    decl, _ = DeclarationTVA.objects.get_or_create(
        configuration=config, annee=annee, periode_num=periode_num,
        defaults={"date_debut": debut, "date_fin": fin},
    )
    decl.date_debut, decl.date_fin = debut, fin
    decl.tva_collectee = res["tva_collectee"]
    decl.tva_deductible = res["tva_deductible"]
    decl.tva_nette = res["tva_nette"]
    decl.save()
    return decl


def _soldes_par_compte(comptes, date_debut, date_fin, sens):
    rows = (
        LigneEcriture.objects.filter(
            compte__in=comptes, piece__statut="VALIDEE",
            piece__date_piece__gte=date_debut, piece__date_piece__lte=date_fin,
        )
        .values("compte_id")
        .annotate(d=Sum("debit"), c=Sum("credit"))
    )
    out = []
    for r in rows:
        d = r["d"] or Decimal("0.00")
        c = r["c"] or Decimal("0.00")
        solde = (c - d) if sens == "CREDITEUR" else (d - c)
        if solde != 0:
            out.append((r["compte_id"], solde))
    return out


@transaction.atomic
def comptabiliser_liquidation(declaration, user) -> PieceComptable:
    if declaration.statut == "VALIDEE":
        raise ValueError("Déclaration déjà liquidée")
    config = declaration.configuration
    exercice = Exercice.objects.get(
        date_debut__lte=declaration.date_fin, date_fin__gte=declaration.date_fin
    )
    piece = PieceComptable.objects.create(
        journal=config.journal, exercice=exercice, date_piece=declaration.date_fin,
        reference=f"TVA-{declaration.annee}-{declaration.periode_num:02d}",
        libelle=f"Liquidation TVA {declaration.periode_num:02d}/{declaration.annee}",
        statut="BROUILLARD", auteur=user,
    )
    n = 1
    for compte_id, solde in _soldes_par_compte(
        config.comptes_collectee.all(), declaration.date_debut, declaration.date_fin, "CREDITEUR"
    ):
        LigneEcriture.objects.create(
            piece=piece, numero_ligne=n, compte_id=compte_id,
            libelle="Solde TVA collectée", debit=solde, credit=Decimal("0.00"),
        )
        n += 1
    for compte_id, solde in _soldes_par_compte(
        config.comptes_deductible.all(), declaration.date_debut, declaration.date_fin, "DEBITEUR"
    ):
        LigneEcriture.objects.create(
            piece=piece, numero_ligne=n, compte_id=compte_id,
            libelle="Solde TVA déductible", debit=Decimal("0.00"), credit=solde,
        )
        n += 1
    nette = declaration.tva_nette
    if nette > 0:
        LigneEcriture.objects.create(
            piece=piece, numero_ligne=n, compte=config.compte_tva_due,
            libelle="TVA due", debit=Decimal("0.00"), credit=nette,
        )
    elif nette < 0:
        LigneEcriture.objects.create(
            piece=piece, numero_ligne=n, compte=config.compte_credit_tva,
            libelle="Crédit de TVA", debit=-nette, credit=Decimal("0.00"),
        )
    valider_piece(piece, user)
    declaration.statut = "VALIDEE"
    declaration.piece_liquidation = piece
    declaration.save(update_fields=["statut", "piece_liquidation"])
    return piece


def generer_bordereau_pdf(declaration) -> bytes:
    from apps.imports_exports.services.pdf import render_pdf

    return render_pdf("fiscal/bordereau_tva.html", {"declaration": declaration})


def resultat_comptable(exercice) -> Decimal:
    """Produits (classe 7) − charges (classe 6) sur les écritures validées."""
    rows = (
        LigneEcriture.objects.filter(piece__exercice=exercice, piece__statut="VALIDEE")
        .values("compte__classe")
        .annotate(d=Sum("debit"), c=Sum("credit"))
    )
    produits = charges = Decimal("0.00")
    for r in rows:
        d = r["d"] or Decimal("0.00")
        c = r["c"] or Decimal("0.00")
        if r["compte__classe"] == 7:
            produits += c - d
        elif r["compte__classe"] == 6:
            charges += d - c
    return produits - charges


def recalculer(declaration):
    reint = declaration.retraitements.filter(sens="REINTEGRATION").aggregate(s=Sum("montant"))["s"] or Decimal("0.00")
    deduc = declaration.retraitements.filter(sens="DEDUCTION").aggregate(s=Sum("montant"))["s"] or Decimal("0.00")
    declaration.total_reintegrations = reint
    declaration.total_deductions = deduc
    declaration.resultat_fiscal = declaration.resultat_comptable + reint - deduc
    base = declaration.resultat_fiscal if declaration.resultat_fiscal > 0 else Decimal("0.00")
    taux = declaration.configuration.taux
    declaration.impot = (base * taux / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    declaration.save()
    return declaration


@transaction.atomic
def creer_declaration_is(config, exercice, user):
    decl, _ = DeclarationIS.objects.get_or_create(configuration=config, exercice=exercice)
    decl.resultat_comptable = resultat_comptable(exercice)
    decl.save(update_fields=["resultat_comptable"])
    return recalculer(decl)


def generer_bordereau_is_pdf(declaration) -> bytes:
    from apps.imports_exports.services.pdf import render_pdf

    return render_pdf("fiscal/bordereau_is.html", {"declaration": declaration})


@transaction.atomic
def comptabiliser_impot(declaration, user):
    if declaration.statut == "VALIDEE":
        raise ValueError("Déclaration IS déjà comptabilisée")
    config = declaration.configuration
    piece = None
    if declaration.impot > 0:
        piece = PieceComptable.objects.create(
            journal=config.journal, exercice=declaration.exercice,
            date_piece=declaration.exercice.date_fin, reference=f"IS-{declaration.exercice.code}",
            libelle=f"Impôt sur les bénéfices {declaration.exercice.code}",
            statut="BROUILLARD", auteur=user,
        )
        LigneEcriture.objects.create(piece=piece, numero_ligne=1, compte=config.compte_charge_impot,
                                     libelle="Charge d'impôt", debit=declaration.impot, credit=Decimal("0.00"))
        LigneEcriture.objects.create(piece=piece, numero_ligne=2, compte=config.compte_dette_impot,
                                     libelle="Dette d'impôt", debit=Decimal("0.00"), credit=declaration.impot)
        valider_piece(piece, user)
        declaration.piece_imposition = piece
    declaration.statut = "VALIDEE"
    declaration.save(update_fields=["statut", "piece_imposition"])
    return piece


@transaction.atomic
def ajouter_retraitement(declaration, libelle, montant, sens):
    rt = RetraitementFiscal.objects.create(declaration=declaration, libelle=libelle, montant=montant, sens=sens)
    recalculer(declaration)
    return rt


@transaction.atomic
def creer_declaration_aib(config, annee, periode_num, base_imposable, user):
    montant = (Decimal(base_imposable) * config.taux / Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    decl, _ = DeclarationAIB.objects.get_or_create(
        configuration=config, annee=annee, periode_num=periode_num,
        defaults={"base_imposable": base_imposable, "montant_aib": montant},
    )
    decl.base_imposable = base_imposable
    decl.montant_aib = montant
    decl.save(update_fields=["base_imposable", "montant_aib"])
    return decl


@transaction.atomic
def comptabiliser_aib(declaration, user):
    if declaration.statut == "VALIDEE":
        raise ValueError("Déclaration AIB déjà comptabilisée")
    config = declaration.configuration
    piece = None
    if declaration.montant_aib > 0:
        exercice = Exercice.objects.get(date_debut__year=declaration.annee)
        piece = PieceComptable.objects.create(
            journal=config.journal, exercice=exercice,
            date_piece=date(declaration.annee, declaration.periode_num, 1),
            reference=f"AIB-{declaration.annee}-{declaration.periode_num:02d}",
            libelle=f"AIB {declaration.periode_num:02d}/{declaration.annee}",
            statut="BROUILLARD", auteur=user,
        )
        LigneEcriture.objects.create(piece=piece, numero_ligne=1, compte=config.compte_aib,
                                     libelle="AIB - acompte", debit=declaration.montant_aib, credit=Decimal("0.00"))
        LigneEcriture.objects.create(piece=piece, numero_ligne=2, compte=config.compte_tresorerie,
                                     libelle="Paiement AIB", debit=Decimal("0.00"), credit=declaration.montant_aib)
        valider_piece(piece, user)
        declaration.piece = piece
    declaration.statut = "VALIDEE"
    declaration.save(update_fields=["statut", "piece"])
    return piece


def generer_bordereau_aib_pdf(declaration) -> bytes:
    from apps.imports_exports.services.pdf import render_pdf

    return render_pdf("fiscal/bordereau_aib.html", {"declaration": declaration})
