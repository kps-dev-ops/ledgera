"""Générateur de fichier FEC français conforme BOI-CF-IOR-60-40-20.

Format : 18 colonnes séparées par tabulation, encodage UTF-8 sans BOM,
ordre chronologique de validation par journal/numéro/ligne.
Dates au format YYYYMMDD, montants au format français (virgule décimale,
pas de séparateur de milliers).
"""
from collections.abc import Iterable
from io import StringIO

from apps.comptabilite.models import LigneEcriture

FEC_COLONNES = [
    "JournalCode", "JournalLib", "EcritureNum", "EcritureDate",
    "CompteNum", "CompteLib", "CompAuxNum", "CompAuxLib",
    "PieceRef", "PieceDate", "EcritureLib", "Debit", "Credit",
    "EcritureLet", "DateLet", "ValidDate", "Montantdevise", "Idevise",
]


def _montant_fr(d) -> str:
    if not d:
        return "0,00"
    return f"{d:.2f}".replace(".", ",")


def _safe(s: str) -> str:
    if s is None:
        return ""
    return str(s).replace("\t", " ").replace("\n", " ").replace("\r", " ")


def _date(d) -> str:
    return d.strftime("%Y%m%d") if d else ""


def _row(ligne: LigneEcriture) -> list[str]:
    p = ligne.piece
    return [
        _safe(p.journal.code),
        _safe(p.journal.libelle),
        str(p.numero or ""),
        _date(p.date_piece),
        _safe(ligne.compte.numero),
        _safe(ligne.compte.libelle),
        _safe(ligne.tiers.code_auxiliaire) if ligne.tiers else "",
        _safe(ligne.tiers.raison_sociale) if ligne.tiers else "",
        _safe(p.reference),
        _date(p.date_piece),
        _safe(ligne.libelle or p.libelle),
        _montant_fr(ligne.debit),
        _montant_fr(ligne.credit),
        _safe(ligne.lettre_lettrage),
        "",  # DateLet — pas implémentée en V1
        _date(p.date_validation.date() if p.date_validation else None),
        "",  # Montantdevise — pas de multidevise dans la pièce V1
        "",  # Idevise
    ]


def build_fec(exercice) -> str:
    """Construit le contenu FEC complet pour l'exercice."""
    qs: Iterable[LigneEcriture] = (
        LigneEcriture.objects.filter(piece__exercice=exercice, piece__statut="VALIDEE")
        .select_related("piece", "piece__journal", "compte", "tiers")
        .order_by("piece__journal__code", "piece__numero", "numero_ligne")
    )
    out = StringIO()
    out.write("\t".join(FEC_COLONNES) + "\n")
    for ligne in qs:
        out.write("\t".join(_row(ligne)) + "\n")
    return out.getvalue()


def build_fec_filename(societe_code: str, exercice_code: str) -> str:
    """FEC_<code-societe>_<code-exercice>.txt — nom canonique pour téléchargement."""
    return f"FEC_{societe_code}_{exercice_code}.txt"
