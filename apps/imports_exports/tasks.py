"""Tâches Celery pour les exports et imports asynchrones.

Tous les exports créent un fichier dans MEDIA_ROOT/exports/ et marquent
l'ExportJob comme TERMINE. En cas d'erreur, statut=ERREUR + message.
"""
from datetime import datetime

from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.files.base import ContentFile
from django.utils import timezone
from django_tenants.utils import schema_context

logger = get_task_logger(__name__)


def _set_erreur(job, e):
    job.statut = "ERREUR"
    job.erreur = str(e)
    job.date_fin = timezone.now()
    job.save()


@shared_task
def import_excel_pieces(job_id: int, schema_name: str):
    """Importe un fichier Excel d'écritures, crée les pièces en BROUILLARD."""
    from django.contrib.auth import get_user_model
    from django.db import transaction

    from apps.comptabilite.models import Exercice, Journal, LigneEcriture, PieceComptable

    from .models import ImportJob
    from .services.parsers import parse_excel_pieces

    User = get_user_model()
    with schema_context(schema_name):
        job = ImportJob.objects.get(pk=job_id)
        try:
            job.statut = "EN_COURS"
            job.save(update_fields=["statut"])
            exercice = Exercice.objects.get(code=job.exercice_code)
            journal = Journal.objects.get(code=job.journal_code)
            user = job.cree_par if isinstance(job.cree_par, User) else User.objects.get(pk=job.cree_par_id)

            pieces_data, erreurs = parse_excel_pieces(job.fichier.path, exercice, journal)
            job.nb_lignes_traitees = sum(len(p["lignes"]) for p in pieces_data) + len(erreurs)

            if erreurs:
                job.statut = "ERREUR"
                job.rapport = {"erreurs": erreurs, "pieces_valides": len(pieces_data)}
            else:
                with transaction.atomic():
                    for pdata in pieces_data:
                        piece = PieceComptable.objects.create(
                            journal=pdata["journal"], exercice=pdata["exercice"],
                            date_piece=pdata["date_piece"], reference=pdata["reference"],
                            libelle=pdata["libelle"], statut="BROUILLARD", auteur=user,
                        )
                        for i, ldata in enumerate(pdata["lignes"], start=1):
                            LigneEcriture.objects.create(
                                piece=piece, numero_ligne=i,
                                compte=ldata["compte"], tiers=ldata["tiers"],
                                libelle=ldata["libelle"],
                                debit=ldata["debit"], credit=ldata["credit"],
                            )
                job.statut = "TERMINE"
                job.nb_pieces_creees = len(pieces_data)
                job.rapport = {"pieces_creees": len(pieces_data)}

            job.date_fin = timezone.now()
            job.save()
        except Exception as e:
            logger.exception("Import Excel KO")
            job.statut = "ERREUR"
            job.rapport = {"exception": str(e)}
            job.date_fin = timezone.now()
            job.save()


@shared_task
def export_balance_excel(job_id: int, schema_name: str):
    from apps.comptabilite.models import Exercice

    from .models import ExportJob
    from .services.excel import build_balance_xlsx

    with schema_context(schema_name):
        job = ExportJob.objects.get(pk=job_id)
        try:
            job.statut = "EN_COURS"
            job.save(update_fields=["statut"])
            exercice = Exercice.objects.get(code=job.parametres["exercice"])
            content = build_balance_xlsx(exercice)
            filename = f"balance_{exercice.code}_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
            job.fichier.save(filename, ContentFile(content), save=False)
            job.statut = "TERMINE"
            job.date_fin = timezone.now()
            job.save()
        except Exception as e:
            logger.exception("Export balance KO")
            _set_erreur(job, e)


@shared_task
def export_grand_livre_excel(job_id: int, schema_name: str):
    from apps.comptabilite.models import CompteComptable, Exercice

    from .models import ExportJob
    from .services.excel import build_grand_livre_xlsx

    with schema_context(schema_name):
        job = ExportJob.objects.get(pk=job_id)
        try:
            job.statut = "EN_COURS"
            job.save(update_fields=["statut"])
            exercice = Exercice.objects.get(code=job.parametres["exercice"])
            compte = CompteComptable.objects.get(numero=job.parametres["compte"])
            content = build_grand_livre_xlsx(compte, exercice)
            filename = f"GL_{compte.numero}_{exercice.code}.xlsx"
            job.fichier.save(filename, ContentFile(content), save=False)
            job.statut = "TERMINE"
            job.date_fin = timezone.now()
            job.save()
        except Exception as e:
            _set_erreur(job, e)


@shared_task
def export_journal_excel(job_id: int, schema_name: str):
    from apps.comptabilite.models import Exercice, Journal

    from .models import ExportJob
    from .services.excel import build_journal_xlsx

    with schema_context(schema_name):
        job = ExportJob.objects.get(pk=job_id)
        try:
            job.statut = "EN_COURS"
            job.save(update_fields=["statut"])
            exercice = Exercice.objects.get(code=job.parametres["exercice"])
            journal_obj = Journal.objects.get(code=job.parametres["journal"])
            content = build_journal_xlsx(journal_obj, exercice)
            filename = f"journal_{journal_obj.code}_{exercice.code}.xlsx"
            job.fichier.save(filename, ContentFile(content), save=False)
            job.statut = "TERMINE"
            job.date_fin = timezone.now()
            job.save()
        except Exception as e:
            _set_erreur(job, e)


@shared_task
def export_fec(job_id: int, schema_name: str):
    from apps.comptabilite.models import Exercice
    from apps.tenants.models import Societe

    from .models import ExportJob
    from .services.fec import build_fec, build_fec_filename

    with schema_context(schema_name):
        job = ExportJob.objects.get(pk=job_id)
        try:
            job.statut = "EN_COURS"
            job.save(update_fields=["statut"])
            exercice = Exercice.objects.get(code=job.parametres["exercice"])
            societe = Societe.objects.get(schema_name=schema_name)
            content = build_fec(exercice).encode("utf-8")
            filename = build_fec_filename(societe.code, exercice.code)
            job.fichier.save(filename, ContentFile(content), save=False)
            job.statut = "TERMINE"
            job.date_fin = timezone.now()
            job.save()
        except Exception as e:
            _set_erreur(job, e)


def _export_pdf_generique(job_id, schema_name, type_label, template, context_builder, filename_builder):
    from .models import ExportJob
    from .services.pdf import render_pdf

    with schema_context(schema_name):
        job = ExportJob.objects.get(pk=job_id)
        try:
            job.statut = "EN_COURS"
            job.save(update_fields=["statut"])
            ctx = context_builder(job)
            content = render_pdf(template, ctx)
            filename = filename_builder(job, ctx)
            job.fichier.save(filename, ContentFile(content), save=False)
            job.statut = "TERMINE"
            job.date_fin = timezone.now()
            job.save()
        except Exception as e:
            logger.exception(f"Export {type_label} KO")
            _set_erreur(job, e)


@shared_task
def export_bilan_pdf(job_id: int, schema_name: str):
    from apps.comptabilite.models import Exercice
    from apps.etats.services.bilan import compute_bilan

    def ctx(job):
        ex = Exercice.objects.get(code=job.parametres["exercice"])
        return compute_bilan(ex)
    _export_pdf_generique(
        job_id, schema_name, "bilan",
        "imports_exports/pdf/bilan_pdf.html",
        ctx,
        lambda job, c: f"bilan_{c['exercice'].code}.pdf",
    )


@shared_task
def export_cr_pdf(job_id: int, schema_name: str):
    from apps.comptabilite.models import Exercice
    from apps.etats.services.compte_resultat import compute_compte_resultat

    def ctx(job):
        ex = Exercice.objects.get(code=job.parametres["exercice"])
        return compute_compte_resultat(ex)
    _export_pdf_generique(
        job_id, schema_name, "compte_resultat",
        "imports_exports/pdf/compte_resultat_pdf.html",
        ctx,
        lambda job, c: f"compte_resultat_{c['exercice'].code}.pdf",
    )


@shared_task
def export_balance_pdf(job_id: int, schema_name: str):
    from apps.comptabilite.models import Exercice
    from apps.etats import selectors

    def ctx(job):
        ex = Exercice.objects.get(code=job.parametres["exercice"])
        lignes = list(selectors.balance(ex))
        td = sum((row["total_debit"] or 0) for row in lignes)
        tc = sum((row["total_credit"] or 0) for row in lignes)
        return {"exercice": ex, "lignes": lignes, "total_debit": td, "total_credit": tc, "equilibre": td == tc}
    _export_pdf_generique(
        job_id, schema_name, "balance",
        "imports_exports/pdf/balance_pdf.html",
        ctx,
        lambda job, c: f"balance_{c['exercice'].code}.pdf",
    )
