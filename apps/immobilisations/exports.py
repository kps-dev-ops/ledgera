from datetime import date
from io import BytesIO

from openpyxl import Workbook

from .selectors import tableau_immobilisations

COLONNES = ["Code", "Désignation", "Catégorie", "Date acq.", "Coût", "Cumul amort.", "VNC", "Statut"]


def tableau_immobilisations_xlsx(date_reference: date) -> bytes:
    """Génère le tableau des immobilisations au format Excel (bytes)."""
    wb = Workbook(write_only=True)
    ws = wb.create_sheet("Immobilisations")
    ws.append(COLONNES)
    for ligne in tableau_immobilisations(date_reference):
        ws.append([
            ligne["code"], ligne["designation"], ligne["categorie"], ligne["date_acquisition"],
            float(ligne["cout_acquisition"]), float(ligne["cumul_amortissements"]),
            float(ligne["vnc"]), ligne["statut"],
        ])
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
