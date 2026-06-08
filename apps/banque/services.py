import csv
from datetime import date, datetime
from decimal import Decimal
from io import TextIOWrapper

from django.db import transaction
from openpyxl import load_workbook

from .models import LigneReleve, ReleveBancaire


def _parse_date(v) -> date:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return datetime.strptime(str(v).strip()[:10], "%Y-%m-%d").date()


@transaction.atomic
def creer_releve_depuis_lignes(compte_bancaire, lignes: list[dict], *, date_debut, date_fin,
                               solde_initial=Decimal("0.00"), solde_final=Decimal("0.00"),
                               fichier_source=None) -> ReleveBancaire:
    """Crée un ReleveBancaire + ses LigneReleve à partir d'une liste de dicts
    {date_operation, libelle, montant (signé), reference_banque}.
    """
    releve = ReleveBancaire.objects.create(
        compte_bancaire=compte_bancaire, date_debut=date_debut, date_fin=date_fin,
        solde_initial=solde_initial, solde_final=solde_final, fichier_source=fichier_source,
    )
    objets = [
        LigneReleve(
            releve=releve, date_operation=ligne["date_operation"], libelle=ligne.get("libelle", ""),
            montant=ligne["montant"], reference_banque=ligne.get("reference_banque", ""),
        )
        for ligne in lignes
    ]
    LigneReleve.objects.bulk_create(objets)
    return releve


def lire_lignes_excel(fichier_path) -> list[dict]:
    """Lit un relevé Excel : en-têtes (1re ligne) date, libelle, montant, reference."""
    wb = load_workbook(fichier_path, read_only=True, data_only=True)
    ws = wb.active
    rows = ws.iter_rows(values_only=True)
    entetes = [str(h).strip().lower() if h else "" for h in next(rows)]
    idx = {nom: i for i, nom in enumerate(entetes)}
    lignes = []
    for row in rows:
        if row is None or all(c is None for c in row):
            continue
        lignes.append({
            "date_operation": _parse_date(row[idx["date"]]),
            "libelle": str(row[idx["libelle"]] or ""),
            "montant": Decimal(str(row[idx["montant"]])),
            "reference_banque": str(row[idx["reference"]] or "") if "reference" in idx else "",
        })
    return lignes


def lire_lignes_csv(fichier) -> list[dict]:
    """Lit un relevé CSV (séparateur ';' ou ','), colonnes date, libelle, montant, reference."""
    if hasattr(fichier, "read"):
        wrapper = TextIOWrapper(fichier, encoding="utf-8-sig")
    else:
        wrapper = open(fichier, encoding="utf-8-sig")  # noqa: SIM115
    sample = wrapper.read(2048)
    wrapper.seek(0)
    dialect = csv.Sniffer().sniff(sample, delimiters=";,")
    reader = csv.DictReader(wrapper, dialect=dialect)
    lignes = []
    for row in reader:
        row = {(k or "").strip().lower(): v for k, v in row.items()}
        lignes.append({
            "date_operation": _parse_date(row["date"]),
            "libelle": row.get("libelle", ""),
            "montant": Decimal(str(row["montant"]).replace(" ", "").replace(",", ".")),
            "reference_banque": row.get("reference", ""),
        })
    return lignes
