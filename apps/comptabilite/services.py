from decimal import Decimal

from django.db import connection, transaction
from django.db.models import Sum
from django.utils import timezone

from .models import CompteComptable, Exercice, Journal, LigneEcriture, Periode, PieceComptable

JOURNAUX_PAR_DEFAUT = [
    ("ACH", "Journal des achats", "ACHATS"),
    ("VTE", "Journal des ventes", "VENTES"),
    ("BQ1", "Banque principale", "BANQUE"),
    ("CA", "Caisse", "CAISSE"),
    ("OD", "Opérations diverses", "OD"),
    ("AN", "À-nouveaux", "AN"),
]


@transaction.atomic
def valider_piece(piece: PieceComptable, user) -> PieceComptable:
    """Bascule une pièce de BROUILLARD à VALIDEE.

    - recalcule total_debit / total_credit depuis les lignes
    - vérifie l'équilibre (R1, doublé en Python pour message UX clair)
    - attribue un numéro via advisory lock par (journal, exercice) (R4)
    - les triggers PG (R1/R2/R3/R5/R7) restent le garde-fou final
    """
    if piece.statut != "BROUILLARD":
        raise ValueError(f"Seule une pièce en BROUILLARD peut être validée (statut: {piece.statut})")

    totaux = piece.lignes.aggregate(d=Sum("debit"), c=Sum("credit"))
    piece.total_debit = totaux["d"] or Decimal("0.00")
    piece.total_credit = totaux["c"] or Decimal("0.00")
    if piece.total_debit == 0:
        raise ValueError("Pièce vide : aucune ligne à valider")
    if piece.total_debit != piece.total_credit:
        raise ValueError(
            f"R1 : pièce non équilibrée (débit={piece.total_debit} / crédit={piece.total_credit})"
        )

    with connection.cursor() as c:
        c.execute(
            "SELECT pg_advisory_xact_lock(hashtext(%s))",
            [f"piece_seq:{piece.journal_id}:{piece.exercice_id}"],
        )
        c.execute(
            "SELECT COALESCE(MAX(numero), 0) + 1 FROM comptabilite_piececomptable "
            "WHERE journal_id = %s AND exercice_id = %s AND numero IS NOT NULL",
            [piece.journal_id, piece.exercice_id],
        )
        piece.numero = c.fetchone()[0]

    piece.statut = "VALIDEE"
    piece.date_validation = timezone.now()
    piece.validee_par = user
    piece.save()
    return piece


@transaction.atomic
def extourner_piece(piece: PieceComptable, user) -> PieceComptable:
    """Crée une pièce d'extourne (lignes inversées débit/crédit)."""
    if piece.statut != "VALIDEE":
        raise ValueError("Seule une pièce VALIDEE peut être extournée")

    extourne = PieceComptable.objects.create(
        journal=piece.journal,
        exercice=piece.exercice,
        date_piece=timezone.now().date(),
        reference=f"EXT-{piece.numero}",
        libelle=f"Extourne de {piece.journal.code} #{piece.numero} — {piece.libelle}",
        statut="BROUILLARD",
        auteur=user,
    )
    for ligne in piece.lignes.all():
        LigneEcriture.objects.create(
            piece=extourne,
            numero_ligne=ligne.numero_ligne,
            compte=ligne.compte,
            tiers=ligne.tiers,
            libelle=f"Extourne : {ligne.libelle}",
            debit=ligne.credit,
            credit=ligne.debit,
        )
    valider_piece(extourne, user)

    piece.statut = "EXTOURNEE"
    piece.piece_extournee = extourne
    piece.save(update_fields=["statut", "piece_extournee"])
    return extourne


def _next_lettre(existing: set[str]) -> str:
    """Retourne la prochaine lettre de lettrage (A..Z, AA..AZ, BA..)."""
    for i in range(1, 27 * 27 * 27):
        n = i
        s = ""
        while n > 0:
            n, r = divmod(n - 1, 26)
            s = chr(ord("A") + r) + s
        if s not in existing:
            return s
    raise RuntimeError("Plus de lettres de lettrage disponibles")


@transaction.atomic
def lettrer(lignes_qs, code_lettre: str | None = None) -> str:
    """Lettre un ensemble de lignes (même tiers, débit total = crédit total)."""
    lignes = list(lignes_qs.select_for_update())
    if len(lignes) < 2:
        raise ValueError("Le lettrage nécessite au moins 2 lignes")
    tiers_ids = {ligne.tiers_id for ligne in lignes}
    if len(tiers_ids) != 1 or None in tiers_ids:
        raise ValueError("Toutes les lignes doivent appartenir au même tiers")
    total_d = sum((ligne.debit for ligne in lignes), Decimal("0.00"))
    total_c = sum((ligne.credit for ligne in lignes), Decimal("0.00"))
    if total_d != total_c:
        raise ValueError(f"Lettrage déséquilibré : débit={total_d} / crédit={total_c}")
    if any(ligne.lettre_lettrage for ligne in lignes):
        raise ValueError("Une ou plusieurs lignes sont déjà lettrées")

    if code_lettre is None:
        tiers_id = tiers_ids.pop()
        existing = set(
            LigneEcriture.objects.filter(tiers_id=tiers_id)
            .exclude(lettre_lettrage="")
            .values_list("lettre_lettrage", flat=True)
        )
        code_lettre = _next_lettre(existing)

    LigneEcriture.objects.filter(pk__in=[ligne.pk for ligne in lignes]).update(lettre_lettrage=code_lettre)
    return code_lettre


@transaction.atomic
def delettrer(tiers_id: int, code_lettre: str) -> int:
    """Annule un lettrage. Retourne le nombre de lignes délettrées."""
    return LigneEcriture.objects.filter(tiers_id=tiers_id, lettre_lettrage=code_lettre).update(
        lettre_lettrage=""
    )


@transaction.atomic
def init_plan_comptable_pour_societe(societe) -> int:
    """Clone les CompteType du plan de la société en CompteComptable du tenant.
    À appeler dans le contexte du schema tenant. Idempotent.
    """
    from apps.referentiels.models import CompteType

    if not societe.plan_comptes_type_id:
        return 0
    crees = 0
    for ct in CompteType.objects.filter(plan=societe.plan_comptes_type).order_by("numero"):
        _, created = CompteComptable.objects.get_or_create(
            numero=ct.numero,
            defaults={
                "libelle": ct.libelle,
                "classe": ct.classe,
                "sens": ct.sens,
                "collectif_tiers": ct.collectif_tiers,
                "analytique_ok": ct.analytique_ok,
            },
        )
        if created:
            crees += 1
    return crees


@transaction.atomic
def init_journaux_par_defaut() -> int:
    """Crée les journaux standards SYSCOHADA. Idempotent."""
    crees = 0
    for code, libelle, type_journal in JOURNAUX_PAR_DEFAUT:
        _, created = Journal.objects.get_or_create(
            code=code, defaults={"libelle": libelle, "type_journal": type_journal}
        )
        if created:
            crees += 1
    return crees


@transaction.atomic
def init_exercice_courant(annee: int = 2026) -> Exercice:
    """Crée l'exercice de l'année donnée (01/01 → 31/12) + ses 12 périodes. Idempotent."""
    from datetime import date

    exercice, _ = Exercice.objects.get_or_create(
        code=str(annee),
        defaults={"date_debut": date(annee, 1, 1), "date_fin": date(annee, 12, 31)},
    )
    for mois in range(1, 13):
        Periode.objects.get_or_create(exercice=exercice, mois=mois)
    return exercice


@transaction.atomic
def cloturer_exercice(exercice: Exercice, user, compte_report: str = "12") -> PieceComptable:
    """Clôture R9 : génère les à-nouveaux dans l'exercice suivant et verrouille
    l'exercice clos. Refuse s'il reste des brouillards ou si déjà clôturé.
    """
    from datetime import date

    if exercice.statut == "CLOTURE":
        raise ValueError("Exercice déjà clôturé")
    nb_brouillards = PieceComptable.objects.filter(exercice=exercice, statut="BROUILLARD").count()
    if nb_brouillards:
        raise ValueError(f"{nb_brouillards} pièce(s) en brouillard à valider ou supprimer avant clôture")

    report, _ = CompteComptable.objects.get_or_create(
        numero=compte_report,
        defaults={"libelle": "Report à nouveau", "classe": 1, "sens": "MIXTE"},
    )

    annee_suivante = exercice.date_fin.year + 1
    exercice_suivant, _ = Exercice.objects.get_or_create(
        code=str(annee_suivante),
        defaults={
            "date_debut": date(annee_suivante, 1, 1),
            "date_fin": date(annee_suivante, 12, 31),
            "exercice_precedent": exercice,
        },
    )
    for mois in range(1, 13):
        Periode.objects.get_or_create(exercice=exercice_suivant, mois=mois)

    soldes = (
        LigneEcriture.objects.filter(
            piece__exercice=exercice, piece__statut="VALIDEE", compte__classe__lte=5
        )
        .values("compte_id", "tiers_id")
        .annotate(d=Sum("debit"), c=Sum("credit"))
    )

    journal_an = Journal.objects.get(code="AN")
    piece = PieceComptable.objects.create(
        journal=journal_an, exercice=exercice_suivant, date_piece=exercice_suivant.date_debut,
        reference=f"AN-{annee_suivante}", libelle=f"À-nouveaux {annee_suivante} (clôture {exercice.code})",
        statut="BROUILLARD", auteur=user,
    )
    numero_ligne = 1
    total = Decimal("0.00")
    for s in soldes:
        solde = (s["d"] or Decimal("0.00")) - (s["c"] or Decimal("0.00"))
        if solde == 0:
            continue
        LigneEcriture.objects.create(
            piece=piece, numero_ligne=numero_ligne, compte_id=s["compte_id"], tiers_id=s["tiers_id"],
            libelle="À-nouveau", debit=solde if solde > 0 else Decimal("0.00"),
            credit=-solde if solde < 0 else Decimal("0.00"),
        )
        numero_ligne += 1
        total += solde

    if total != 0:
        LigneEcriture.objects.create(
            piece=piece, numero_ligne=numero_ligne, compte=report,
            libelle="Report à nouveau (résultat)",
            debit=-total if total < 0 else Decimal("0.00"),
            credit=total if total > 0 else Decimal("0.00"),
        )

    valider_piece(piece, user)

    Periode.objects.filter(exercice=exercice).update(statut="CLOTUREE")
    exercice.statut = "CLOTURE"
    exercice.date_cloture = timezone.now()
    exercice.cloture_par = user
    exercice.save(update_fields=["statut", "date_cloture", "cloture_par"])
    return piece
