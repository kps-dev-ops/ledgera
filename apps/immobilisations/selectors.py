from datetime import date
from decimal import Decimal

from django.db.models import Sum

from apps.comptabilite.models import LigneEcriture

from .models import Immobilisation


def tableau_immobilisations(date_reference: date) -> list[dict]:
    """Listing complet avec cumul amortissements comptabilisés et VNC à la date."""
    resultat = []
    for immo in Immobilisation.objects.select_related("categorie").all():
        cumul = (
            immo.dotations.filter(
                statut="COMPTABILISEE", piece_generee__date_piece__lte=date_reference
            ).aggregate(s=Sum("montant"))["s"]
            or Decimal("0.00")
        )
        resultat.append({
            "code": immo.code,
            "designation": immo.designation,
            "categorie": immo.categorie.libelle,
            "date_acquisition": immo.date_acquisition,
            "cout_acquisition": immo.cout_acquisition,
            "cumul_amortissements": cumul,
            "vnc": immo.cout_acquisition - cumul,
            "statut": immo.statut,
        })
    return resultat


def controle_coherence(date_reference: date) -> dict:
    """Rapproche le total VNC du solde comptable (Σ 2x - Σ 28x). Pour test/contrôle."""
    total_vnc = sum(
        (row["vnc"] for row in tableau_immobilisations(date_reference)), Decimal("0.00")
    )
    soldes = LigneEcriture.objects.filter(
        piece__statut="VALIDEE", piece__date_piece__lte=date_reference, compte__classe=2
    ).aggregate(d=Sum("debit"), c=Sum("credit"))
    solde_classe2 = (soldes["d"] or Decimal("0.00")) - (soldes["c"] or Decimal("0.00"))
    return {"total_vnc": total_vnc, "solde_comptable_classe2": solde_classe2}
