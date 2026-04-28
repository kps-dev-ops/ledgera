from django.contrib import admin

from .models import ExportJob, ImportJob


@admin.register(ImportJob)
class ImportJobAdmin(admin.ModelAdmin):
    list_display = ("pk", "modele", "journal_code", "statut", "nb_pieces_creees", "cree_par", "date_creation")
    list_filter = ("statut", "modele")
    readonly_fields = ("date_creation", "date_fin", "rapport", "nb_lignes_traitees", "nb_pieces_creees")


@admin.register(ExportJob)
class ExportJobAdmin(admin.ModelAdmin):
    list_display = ("pk", "type_export", "statut", "cree_par", "date_creation", "date_fin")
    list_filter = ("statut", "type_export")
    readonly_fields = ("date_creation", "date_fin", "fichier")
